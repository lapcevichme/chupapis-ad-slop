import json
import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from app.contracts.creative_json import BannerContent, PromoContent
from app.infra.agent.patterns import SvgPatternGenerator
from app.infra.agent.prompts import load_prompt
from app.infra.creative_validation import validate_banner_json, validate_content_json
from app.infra.llm import ImageGenerator, with_cache_breakpoints

MAX_ATTEMPTS = 3
# Сторис: картинка — фон всего экрана, текст поверх. Смарт-баннер: картинка — фон всей карточки, текст слева поверх.
IMAGE_SIZES = {"STORY": "1024x1536", "SMART_BANNER": "1536x1024"}
# Вид кадра для фона-паттерна: где лежит текст и куда можно ставить акценты.
PATTERN_KINDS = {"STORY": "STORY", "SMART_BANNER": "CARD"}
# На промо-экране картинка стоит над текстом во всю ширину. Квадрат занимал почти половину экрана, и промо-экран
# не влезал без прокрутки, поэтому у промо-экрана всегда своя широкая картинка 3:2 (такой кадр умеет gpt-image).
CONTENT_IMAGE_SIZE = "1536x1024"
CONTENT_IMAGE_ASPECT = 1.5
# Своя картинка пользователя: пропорции неизвестны, на промо-экране показываем её той же полосой.
USER_IMAGE_ASPECT = 1.5
# Сторис в превью: экран 280x580, отступы 16. Текст лежит на картинке без подложки и не должен дойти до предмета,
# который занимает нижние 40% кадра. Схема баннера этого не ограничивает, поэтому оцениваем высоту сами.
STORY_TEXT_WIDTH_PX = 248
STORY_TEXT_MAX_HEIGHT_PX = 240
STORY_TEXT_GAP_PX = 8
AVERAGE_CHAR_WIDTH_EM = 0.58
TITLE_LINE_HEIGHT = 1.15
TEXT_LINE_HEIGHT = 1.3
DEFAULT_FONT_SIZE = 16


class DesignResult(BaseModel):
    """Готовый креатив. Тексты на русском, JSON строго по схемам."""

    bannerName: str = Field(description="Короткое служебное название баннера, до 100 символов")
    banner: BannerContent
    contentName: str | None = Field(
        None, description="Название промо-экрана; null, если экран не нужен"
    )
    content: PromoContent | None = Field(
        None, description="PROMO-экран после тапа по баннеру; null, если не нужен"
    )
    imagePrompt: str | None = Field(
        None,
        description="Промпт на английском для генерации картинки баннера: без людей и без текста на картинке",
    )
    contentImagePrompt: str | None = Field(
        None,
        description="Промпт широкой картинки промо-экрана (3:2): тот же предмет по центру, без пустых зон под текст",
    )


class EditChange(BaseModel):
    op: Literal["set", "remove", "insert"] = Field(
        description="set — заменить или добавить значение, remove — убрать, insert — вставить элемент в список"
    )
    path: str = Field(
        description='Путь в документе {"banner": ..., "content": ...} через «/»: "/banner/titleStyle/textColor", '
        '"/content/component/components/1/text". Для insert последний шаг — индекс или «-» (в конец списка)'
    )
    value: Any = Field(None, description="Новое значение для set и insert")


class DesignEdit(BaseModel):
    """Точечная правка готового креатива: меняется только то, о чём просил пользователь."""

    changes: list[EditChange] = Field(min_length=1, description="Изменения по порядку")
    summary: str = Field(description="Что изменено, одной фразой по-русски")
    bannerName: str | None = Field(
        None, description="Новое служебное название баннера, если оно больше не подходит"
    )
    imagePrompt: str | None = Field(
        None, description="Промпт новой картинки баннера, если needImagePrompt"
    )
    contentImagePrompt: str | None = Field(
        None, description="Промпт новой картинки промо-экрана, если needContentImagePrompt"
    )


class PatchError(Exception):
    pass


def apply_changes(document: dict[str, Any], changes: list[dict[str, Any]]) -> dict[str, Any]:
    """Применяет правки дизайнера к копии документа {"banner", "content"}; кривой путь — PatchError с объяснением."""
    doc = deepcopy(document)
    for change in changes:
        path, op = change.get("path", ""), change.get("op")
        parts = [p.replace("~1", "/").replace("~0", "~") for p in path.strip("/").split("/")]
        if len(parts) < 2 or doc.get(parts[0]) is None:
            raise PatchError(
                f"{path}: путь должен начинаться с /banner/ или /content/ существующего документа"
            )
        if parts[:2] == ["banner", "image"]:
            raise PatchError(f"{path}: картинку баннера подставляет система, её не трогай")
        node: Any = doc
        for part in parts[:-1]:
            if isinstance(node, list):
                node = node[_index(path, part, node)]
            elif isinstance(node, dict):
                if part not in node or node[part] is None:
                    if op != "set":
                        raise PatchError(f"{path}: такого поля нет")
                    node[part] = {}
                node = node[part]
            else:
                raise PatchError(f"{path}: {part} не объект и не список")
        last = parts[-1]
        if isinstance(node, list):
            if op == "insert":
                node.insert(
                    len(node) if last == "-" else _index(path, last, node, allow_end=True),
                    change.get("value"),
                )
            elif op == "set":
                node[_index(path, last, node)] = change.get("value")
            else:
                node.pop(_index(path, last, node))
        elif isinstance(node, dict):
            if op == "remove":
                if last not in node:
                    raise PatchError(f"{path}: такого поля нет")
                del node[last]
            else:
                node[last] = change.get("value")
        else:
            raise PatchError(f"{path}: родитель не объект и не список")
    return doc


def _index(path: str, part: str, items: list[Any], allow_end: bool = False) -> int:
    limit = len(items) + (1 if allow_end else 0)
    if not part.isdigit() or int(part) >= limit:
        raise PatchError(f"{path}: индекс {part} вне списка из {len(items)} элементов")
    return int(part)


def _style(
    image_style: str, target: Literal["banner", "content"]
) -> Literal["illustration", "pattern"]:
    if image_style == "mixed":
        return "pattern" if target == "banner" else "illustration"
    return image_style  # type: ignore[return-value]


@dataclass
class EditRequest:
    instruction: str
    banner_type: dict[str, Any]
    banner_name: str
    banner: dict[str, Any]
    # Промо-экран баннера, если он есть: его тоже можно править.
    content: dict[str, Any] | None = None
    generate_image: bool = False
    image_url: str | None = None
    image_style: Literal["illustration", "pattern", "mixed"] = "illustration"

    @property
    def brief(self) -> str:
        # Тема для фона-паттерна: о чём баннер и что просили поменять.
        return " ".join(
            filter(None, [self.banner.get("title"), self.banner.get("text"), self.instruction])
        )

    def style_for(self, target: Literal["banner", "content"]) -> Literal["illustration", "pattern"]:
        return _style(self.image_style, target)


@dataclass
class DesignRequest:
    brief: str
    banner_type: dict[str, Any]
    with_content: bool
    generate_image: bool
    image_url: str | None = None
    previous: dict[str, Any] | None = None
    content_image: bool | None = None
    promo_only: bool = False
    # illustration — растровая картинка с предметом, pattern — SVG-фон, где тема передаётся только цветом,
    # mixed — фон баннера паттерном, картинка промо-экрана иллюстрацией.
    image_style: Literal["illustration", "pattern", "mixed"] = "illustration"

    @property
    def wants_content_image(self) -> bool:
        wanted = self.with_content if self.content_image is None else self.content_image
        return self.generate_image and wanted

    def style_for(self, target: Literal["banner", "content"]) -> Literal["illustration", "pattern"]:
        return _style(self.image_style, target)

    @property
    def previous_image(self) -> str | None:
        return (((self.previous or {}).get("content") or {}).get("image") or {}).get("url")

    def generates_banner_image(self, type_code: str) -> bool:
        # У промо-экрана своя картинка, поэтому просьба «только промо» картинку баннера не трогает.
        return self.generate_image and not self.promo_only


@dataclass
class DesignOutcome:
    banner_name: str
    banner: dict[str, Any]
    content_name: str | None
    content: dict[str, Any] | None
    notes: list[str] = field(default_factory=list)
    content_image: dict[str, Any] | None = None
    # Что поменяла точечная правка, словами дизайнера.
    summary: str | None = None


class DesignError(Exception):
    pass


def _validate(
    args: dict[str, Any],
    banner_type: dict[str, Any],
    with_content: bool,
    *,
    media_base_url: str = "/api/media",
) -> list[str]:
    _, errors = validate_banner_json(
        args.get("banner"),
        type_code=banner_type["code"],
        title_max=banner_type["titleMaxLength"],
        text_max=banner_type["textMaxLength"],
        prefix="banner",
        media_base_url=media_base_url,
    )
    problems = [f"{e.code} {e.field}: {e.message}" for e in errors]
    if not args.get("bannerName"):
        problems.append("bannerName обязателен")
    if with_content:
        if args.get("content") is None:
            problems.append("content обязателен: нужен промо-экран")
        else:
            _, content_errors = validate_content_json(
                args["content"], prefix="content", media_base_url=media_base_url
            )
            problems += [f"{e.code} {e.field}: {e.message}" for e in content_errors]
    return problems


def _text_block_height(text: str | None, style: dict[str, Any] | None, line_height: float) -> float:
    if not text:
        return 0
    font_size = (style or {}).get("fontSize") or DEFAULT_FONT_SIZE
    chars_per_line = STORY_TEXT_WIDTH_PX / (AVERAGE_CHAR_WIDTH_EM * font_size)
    return math.ceil(len(text) / chars_per_line) * font_size * line_height


def story_text_height(banner: dict[str, Any]) -> float:
    """Примерная высота заголовка и текста сторис в пикселях, с теми же межстрочными, что в превью."""
    title = _text_block_height(banner.get("title"), banner.get("titleStyle"), TITLE_LINE_HEIGHT)
    text = _text_block_height(banner.get("text"), banner.get("textStyle"), TEXT_LINE_HEIGHT)
    return title + text + STORY_TEXT_GAP_PX


class Designer:
    def __init__(
        self,
        model: BaseChatModel,
        images: ImageGenerator,
        patterns: SvgPatternGenerator | None = None,
        *,
        cache_enabled: bool = True,
        media_base_url: str = "/api/media",
    ):
        # Без принудительного tool_choice: часть моделей (в том числе Claude 5.5) его не поддерживает.
        self.model = model.bind_tools([DesignResult])
        self.editor = model.bind_tools([DesignEdit])
        self.images = images
        self.patterns = patterns
        self.cache_enabled = cache_enabled
        self.media_base_url = media_base_url

    async def design(
        self, request: DesignRequest, progress: Callable[[str], None] = lambda _: None
    ) -> DesignOutcome:
        t = request.banner_type
        illustration = request.style_for("banner") == "illustration"
        task = {
            "brief": request.brief,
            "bannerType": t["code"],
            "titleMaxLength": t["titleMaxLength"],
            "textMaxLength": t["textMaxLength"],
            "withContent": request.with_content,
            "needImagePrompt": illustration and request.generates_banner_image(t["code"]),
            "imageSize": IMAGE_SIZES.get(t["code"])
            if illustration and request.generates_banner_image(t["code"])
            else None,
            "needContentImagePrompt": request.style_for("content") == "illustration"
            and request.wants_content_image,
            "contentImageSize": CONTENT_IMAGE_SIZE if request.wants_content_image else None,
            "previousVersion": request.previous,
        }
        messages: list[BaseMessage] = [
            SystemMessage(load_prompt("design")),
            HumanMessage(json.dumps(task, ensure_ascii=False)),
        ]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            progress(f"Дизайнер собирает креатив, попытка {attempt}")
            response: AIMessage = await self.model.ainvoke(
                with_cache_breakpoints(messages, stable=1, enabled=self.cache_enabled)
            )
            call = next((c for c in response.tool_calls if c["name"] == "DesignResult"), None)
            if call is None:
                problems = ["модель ответила текстом вместо вызова DesignResult"]
                messages += [
                    response,
                    HumanMessage("Верни результат только вызовом инструмента DesignResult."),
                ]
                continue
            problems = _validate(
                call["args"], t, request.with_content, media_base_url=self.media_base_url
            )
            has_image = request.generate_image or request.image_url or request.previous_image
            if not problems and has_image and t["code"] == "STORY" and attempt < MAX_ATTEMPTS:
                # Длинный текст портит вид, но не ломает кампанию: на последней попытке принимаем как есть.
                height = story_text_height(call["args"]["banner"])
                if height > STORY_TEXT_MAX_HEIGHT_PX:
                    problems = [
                        f"заголовок и текст занимают около {height:.0f}px из {STORY_TEXT_MAX_HEIGHT_PX}px и наедут на картинку: сократи их или уменьши шрифт"
                    ]
            if not problems:
                return await self._finish(call["args"], request, progress)
            messages += [
                response,
                ToolMessage(
                    tool_call_id=call["id"],
                    content="JSON не прошёл проверку, исправь и верни заново:\n"
                    + "\n".join(problems),
                ),
            ]
        raise DesignError("Не удалось собрать валидный JSON: " + "; ".join(problems))

    async def edit(
        self, request: EditRequest, progress: Callable[[str], None] = lambda _: None
    ) -> DesignOutcome:
        """Правит готовый креатив точечно: модель возвращает список изменений, а не новый JSON целиком."""
        t = request.banner_type
        banner = {k: v for k, v in request.banner.items() if k != "image"}
        illustration = request.generate_image and request.style_for("banner") == "illustration"
        content_illustration = (
            request.generate_image
            and request.content is not None
            and request.style_for("content") == "illustration"
        )
        task = {
            "instruction": request.instruction,
            "bannerType": t["code"],
            "titleMaxLength": t["titleMaxLength"],
            "textMaxLength": t["textMaxLength"],
            "bannerName": request.banner_name,
            "document": {"banner": banner, "content": request.content},
            "needImagePrompt": illustration,
            "imageSize": IMAGE_SIZES.get(t["code"]) if illustration else None,
            "needContentImagePrompt": content_illustration,
            "contentImageSize": CONTENT_IMAGE_SIZE if content_illustration else None,
        }
        messages: list[BaseMessage] = [
            SystemMessage(load_prompt("design_edit")),
            HumanMessage(json.dumps(task, ensure_ascii=False)),
        ]
        problems: list[str] = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            progress(f"Дизайнер правит креатив, попытка {attempt}")
            response: AIMessage = await self.editor.ainvoke(
                with_cache_breakpoints(messages, stable=1, enabled=self.cache_enabled)
            )
            call = next((c for c in response.tool_calls if c["name"] == "DesignEdit"), None)
            if call is None:
                problems = ["модель ответила текстом вместо вызова DesignEdit"]
                messages += [
                    response,
                    HumanMessage("Верни правку только вызовом инструмента DesignEdit."),
                ]
                continue
            args = call["args"]
            try:
                edited = apply_changes(
                    {"banner": banner, "content": request.content}, args.get("changes") or []
                )
                name = args.get("bannerName") or request.banner_name
                problems = _validate(
                    {**edited, "bannerName": name},
                    t,
                    request.content is not None,
                    media_base_url=self.media_base_url,
                )
            except PatchError as exc:
                problems = [str(exc)]
            if not problems:
                return await self._finish_edit(args, edited, name, request, progress)
            messages += [
                response,
                ToolMessage(
                    tool_call_id=call["id"],
                    content="Правка не применилась, исправь и верни все изменения заново:\n"
                    + "\n".join(problems),
                ),
            ]
        raise DesignError("Не удалось применить правку: " + "; ".join(problems))

    async def _finish_edit(
        self,
        args: dict[str, Any],
        edited: dict[str, Any],
        name: str,
        request: EditRequest,
        progress: Callable[[str], None],
    ) -> DesignOutcome:
        code = request.banner_type["code"]
        banner = BannerContent.model_validate(edited["banner"]).model_dump(
            mode="json", exclude_none=True
        )
        content = None
        if request.content is not None:
            content = PromoContent.model_validate(edited["content"]).model_dump(
                mode="json", exclude_none=True
            )
        notes: list[str] = []
        banner_url = (request.banner.get("image") or {}).get("url")
        content_image = None
        if request.image_url:
            banner_url = request.image_url
            content_image = {"url": request.image_url, "aspectRatio": USER_IMAGE_ASPECT}
        elif request.generate_image:
            progress("Генерирую картинки" if content is not None else "Генерирую картинку")
            banner_url = (
                await self._picture(
                    request,
                    banner,
                    args.get("imagePrompt"),
                    IMAGE_SIZES[code],
                    PATTERN_KINDS[code],
                    request.style_for("banner"),
                    "Картинка баннера",
                    notes,
                )
                or banner_url
            )
            if content is not None:
                url = await self._picture(
                    request,
                    banner,
                    args.get("contentImagePrompt"),
                    CONTENT_IMAGE_SIZE,
                    "WIDE",
                    request.style_for("content"),
                    "Картинка промо-экрана",
                    notes,
                )
                if url:
                    content_image = {"url": url, "aspectRatio": CONTENT_IMAGE_ASPECT}
        elif (
            banner_url
            and banner_url.endswith(".svg")
            and _colors(banner) != _colors(request.banner)
        ):
            # Паттерн нарисован тон в тон с фоном: после смены цветов старый фон выбивается, а новый стоит копейки.
            progress("Перекрашиваю фон баннера")
            banner_url = (
                await self._pattern(request, banner, PATTERN_KINDS[code], IMAGE_SIZES[code])
                or banner_url
            )
        if banner_url:
            banner["image"] = {"url": banner_url}
        if content is not None and content_image:
            set_content_image(content, content_image)
        return DesignOutcome(
            name[:100], banner, None, content, notes, content_image, args.get("summary")
        )

    async def _picture(
        self,
        request: DesignRequest | EditRequest,
        banner: dict[str, Any],
        prompt: str | None,
        size: str,
        kind: str,
        style: str,
        what: str,
        notes: list[str],
    ) -> str | None:
        """Иллюстрация по промпту или фон-паттерн. Если иллюстрацию сделать не удалось, ставим паттерн."""
        if style == "pattern":
            url = await self._pattern(request, banner, kind, size)
            if url is None:
                notes.append(f"{what}: фон-паттерн сделать не удалось, осталось без изображения")
            return url
        if not prompt:
            return None
        reason = None
        try:
            url = await self.images.generate(prompt, size)
        except Exception as exc:  # генерация — бонус, сценарий без неё не ломается
            url, reason = None, type(exc).__name__
        if url is not None:
            return url
        fallback = await self._pattern(request, banner, kind, size)
        why = f" ({reason})" if reason else ""
        if fallback is not None:
            notes.append(
                f"{what}: иллюстрацию сгенерировать не удалось{why}, вместо неё фон-паттерн"
            )
        else:
            notes.append(f"{what}: сгенерировать не удалось{why}, осталось без изображения")
        return fallback

    async def _pattern(
        self, request: DesignRequest | EditRequest, banner: dict[str, Any], kind: str, size: str
    ) -> str | None:
        if self.patterns is None:
            return None
        # Цвета в баннере в формате #RRGGBBAA, модели паттерна нужен #RRGGBB.
        base = (banner.get("background") or {}).get("color") or "#FFFFFFFF"
        text = (banner.get("titleStyle") or {}).get("textColor") or "#000000FF"
        try:
            return await self.patterns.generate(
                theme=request.brief, kind=kind, base_color=base[:7], text_color=text[:7], size=size
            )
        except Exception:  # паттерн — тоже бонус
            return None

    async def _finish(
        self, args: dict[str, Any], request: DesignRequest, progress: Callable[[str], None]
    ) -> DesignOutcome:
        code = request.banner_type["code"]
        banner = BannerContent.model_validate(args["banner"]).model_dump(
            mode="json", exclude_none=True
        )
        content = None
        if request.with_content and args.get("content"):
            content = PromoContent.model_validate(args["content"]).model_dump(
                mode="json", exclude_none=True
            )
        notes: list[str] = []
        banner_url, content_image = (request.image_url, None)
        if banner_url:
            content_image = {"url": banner_url, "aspectRatio": USER_IMAGE_ASPECT}
        elif request.generate_image:
            own = request.wants_content_image
            progress("Генерирую картинки" if own else "Генерирую картинку")
            if request.generates_banner_image(code):
                banner_url = await self._picture(
                    request,
                    banner,
                    args.get("imagePrompt"),
                    IMAGE_SIZES[code],
                    PATTERN_KINDS[code],
                    request.style_for("banner"),
                    "Картинка баннера",
                    notes,
                )
            own_url = (
                await self._picture(
                    request,
                    banner,
                    args.get("contentImagePrompt"),
                    CONTENT_IMAGE_SIZE,
                    "WIDE",
                    request.style_for("content"),
                    "Картинка промо-экрана",
                    notes,
                )
                if own
                else None
            )
            if own_url:
                content_image = {"url": own_url, "aspectRatio": CONTENT_IMAGE_ASPECT}
        if not banner_url:
            banner_url = request.previous_image
        if banner_url:
            banner["image"] = {"url": banner_url}
        if content is not None and content_image:
            insert_content_image(content, content_image)
        content_name = (args.get("contentName") or "Промо-экран")[:100] if content else None
        return DesignOutcome(
            args["bannerName"][:100], banner, content_name, content, notes, content_image
        )


def _colors(banner: dict[str, Any]) -> tuple[Any, Any]:
    return (banner.get("background") or {}).get("color"), (banner.get("titleStyle") or {}).get(
        "textColor"
    )


def set_content_image(content: dict[str, Any], image: dict[str, Any]) -> None:
    """Заменяет картинку промо-экрана или ставит её первой, если картинки ещё нет."""
    existing = next((c for c in content["component"]["components"] if c["role"] == "image"), None)
    if existing is not None:
        existing.update(image)
    else:
        insert_content_image(content, image)


def insert_content_image(content: dict[str, Any], image: dict[str, Any]) -> None:
    """Ставит картинку первым компонентом промо-экрана, если места хватает и картинки там ещё нет."""
    components = content["component"]["components"]
    if len(components) < 6 and (not any((c["role"] == "image" for c in components))):
        components.insert(0, {"role": "image", **image})
