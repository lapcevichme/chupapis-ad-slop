"""Дизайн-агент: по задаче от чат-агента собирает JSON баннера и PROMO-контента.

Результат проверяется теми же схемами и правилами, что и в API (`app.domain.creatives`).
Ошибки возвращаются модели, и она исправляет JSON, пока он не пройдёт проверку.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from app.agent.llm import ImageGenerator
from app.agent.prompts import load_prompt
from app.domain.creatives import validate_banner_json, validate_content_json
from app.schemas.creative_json import BannerContent, PromoContent

MAX_ATTEMPTS = 3
# Сторис: картинка — фон всего экрана, текст поверх. Смарт-баннер: картинка — квадратная иконка в карточке.
IMAGE_SIZES = {"STORY": "1024x1536", "SMART_BANNER": "1024x1024"}
# На промо-экране картинка стоит над текстом во всю ширину, поэтому там всегда квадрат с предметом на весь кадр.
CONTENT_IMAGE_SIZE = "1024x1024"
CONTENT_IMAGE_ASPECT = 1.0
# Своя картинка пользователя: пропорции неизвестны, на промо-экране показываем её широкой полосой.
USER_IMAGE_ASPECT = 1.5


def needs_own_content_image(type_code: str) -> bool:
    """Фон сторис с пустыми зонами под текст на промо-экране не годится; квадратная иконка смарт-баннера годится."""
    return type_code == "STORY"


class DesignResult(BaseModel):
    """Готовый креатив. Тексты на русском, JSON строго по схемам."""

    bannerName: str = Field(description="Короткое служебное название баннера, до 100 символов")
    banner: BannerContent
    contentName: str | None = Field(None, description="Название промо-экрана; null, если экран не нужен")
    content: PromoContent | None = Field(None, description="PROMO-экран после тапа по баннеру; null, если не нужен")
    imagePrompt: str | None = Field(
        None, description="Промпт на английском для генерации картинки баннера: без людей и без текста на картинке"
    )
    contentImagePrompt: str | None = Field(
        None, description="Только для STORY с промо-экраном: промпт квадратной картинки промо-экрана, предмет на весь кадр"
    )


@dataclass
class DesignRequest:
    brief: str
    banner_type: dict[str, Any]
    with_content: bool
    generate_image: bool
    image_url: str | None = None
    previous: dict[str, Any] | None = None
    # Нужна ли картинка для промо-экрана; по умолчанию — если промо-экран собирается в этом же запросе.
    content_image: bool | None = None
    # Просили картинку только для промо-экрана: картинку баннера не трогаем.
    promo_only: bool = False

    @property
    def wants_content_image(self) -> bool:
        wanted = self.with_content if self.content_image is None else self.content_image
        return self.generate_image and wanted

    @property
    def previous_image(self) -> str | None:
        return (((self.previous or {}).get("content") or {}).get("image") or {}).get("url")

    def generates_banner_image(self, type_code: str) -> bool:
        if not self.generate_image:
            return False
        # Промо-экрану смарт-баннера хватает прежней иконки, промо-экрану сторис нужна своя картинка.
        return not (self.promo_only and (needs_own_content_image(type_code) or self.previous_image))


@dataclass
class DesignOutcome:
    banner_name: str
    banner: dict[str, Any]
    content_name: str | None
    content: dict[str, Any] | None
    notes: list[str] = field(default_factory=list)
    # Картинка для промо-экрана: у сторис своя квадратная, у смарт-баннера та же иконка.
    content_image: dict[str, Any] | None = None


class DesignError(Exception):
    pass


def _validate(args: dict[str, Any], banner_type: dict[str, Any], with_content: bool) -> list[str]:
    _, errors = validate_banner_json(
        args.get("banner"),
        type_code=banner_type["code"],
        title_max=banner_type["titleMaxLength"],
        text_max=banner_type["textMaxLength"],
        prefix="banner",
    )
    problems = [f"{e.code} {e.field}: {e.message}" for e in errors]
    if not args.get("bannerName"):
        problems.append("bannerName обязателен")
    if with_content:
        if args.get("content") is None:
            problems.append("content обязателен: нужен промо-экран")
        else:
            _, content_errors = validate_content_json(args["content"], prefix="content")
            problems += [f"{e.code} {e.field}: {e.message}" for e in content_errors]
    return problems


class Designer:
    def __init__(self, model: BaseChatModel, images: ImageGenerator):
        # Без принудительного tool_choice: часть моделей (в том числе Claude 5.5) его не поддерживает.
        self.model = model.bind_tools([DesignResult])
        self.images = images

    async def design(self, request: DesignRequest, progress: Callable[[str], None] = lambda _: None) -> DesignOutcome:
        t = request.banner_type
        task = {
            "brief": request.brief,
            "bannerType": t["code"],
            "titleMaxLength": t["titleMaxLength"],
            "textMaxLength": t["textMaxLength"],
            "withContent": request.with_content,
            "needImagePrompt": request.generates_banner_image(t["code"]),
            "imageSize": IMAGE_SIZES.get(t["code"]) if request.generates_banner_image(t["code"]) else None,
            "needContentImagePrompt": request.wants_content_image and needs_own_content_image(t["code"]),
            "previousVersion": request.previous,
        }
        messages: list = [SystemMessage(load_prompt("design")), HumanMessage(json.dumps(task, ensure_ascii=False))]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            progress(f"Дизайнер собирает креатив, попытка {attempt}")
            response: AIMessage = await self.model.ainvoke(messages)
            call = next((c for c in response.tool_calls if c["name"] == "DesignResult"), None)
            if call is None:
                problems = ["модель ответила текстом вместо вызова DesignResult"]
                messages += [response, HumanMessage("Верни результат только вызовом инструмента DesignResult.")]
                continue
            problems = _validate(call["args"], t, request.with_content)
            if not problems:
                return await self._finish(call["args"], request, progress)
            messages += [
                response,
                ToolMessage(
                    tool_call_id=call["id"],
                    content="JSON не прошёл проверку, исправь и верни заново:\n" + "\n".join(problems),
                ),
            ]
        raise DesignError("Не удалось собрать валидный JSON: " + "; ".join(problems))

    async def _generate(self, prompt: str | None, size: str, what: str, notes: list[str]) -> str | None:
        if not prompt:
            return None
        try:
            url = await self.images.generate(prompt, size)
        except Exception as exc:  # генерация — бонус, сценарий без неё не ломается
            notes.append(f"{what}: сгенерировать не удалось ({type(exc).__name__}), осталось без изображения")
            return None
        if url is None:
            notes.append(f"{what}: генерация картинок недоступна, осталось без изображения")
        return url

    async def _finish(self, args: dict[str, Any], request: DesignRequest, progress) -> DesignOutcome:
        code = request.banner_type["code"]
        banner = BannerContent.model_validate(args["banner"]).model_dump(mode="json", exclude_none=True)
        content = None
        if request.with_content and args.get("content"):
            content = PromoContent.model_validate(args["content"]).model_dump(mode="json", exclude_none=True)
        notes: list[str] = []

        banner_url, content_image = request.image_url, None
        if banner_url:
            content_image = {"url": banner_url, "aspectRatio": USER_IMAGE_ASPECT}
        elif request.generate_image:
            own = request.wants_content_image and needs_own_content_image(code)
            progress("Генерирую картинки" if own else "Генерирую картинку")
            # Промо-экрану сторис нужна своя квадратная картинка. Генерируем по очереди, а не параллельно:
            # OpenRouter заранее резервирует деньги под каждый запрос, и два сразу упираются в небольшой лимит ключа.
            if request.generates_banner_image(code):
                banner_url = await self._generate(args.get("imagePrompt"), IMAGE_SIZES[code], "Картинка баннера", notes)
            own_url = await self._generate(args.get("contentImagePrompt") if own else None, CONTENT_IMAGE_SIZE, "Картинка промо-экрана", notes)
            icon = banner_url or request.previous_image
            if own_url:
                content_image = {"url": own_url, "aspectRatio": CONTENT_IMAGE_ASPECT}
            elif icon and not needs_own_content_image(code) and request.wants_content_image:
                content_image = {"url": icon, "aspectRatio": CONTENT_IMAGE_ASPECT}
        if not banner_url:
            # Модель картинку не заполняет, поэтому правка без новой генерации оставляет прежнюю.
            banner_url = request.previous_image

        if banner_url:
            banner["image"] = {"url": banner_url}
        if content is not None and content_image:
            insert_content_image(content, content_image)
        content_name = (args.get("contentName") or "Промо-экран")[:100] if content else None
        return DesignOutcome(args["bannerName"][:100], banner, content_name, content, notes, content_image)


def insert_content_image(content: dict[str, Any], image: dict[str, Any]) -> None:
    """Ставит картинку первым компонентом промо-экрана, если места хватает и картинки там ещё нет."""
    components = content["component"]["components"]
    if len(components) < 6 and not any(c["role"] == "image" for c in components):
        components.insert(0, {"role": "image", **image})
