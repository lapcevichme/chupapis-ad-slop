import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, ValidationError

from app.core.errors import ApiError, api_error
from app.infra.agent.designer import (
    Designer,
    DesignError,
    DesignRequest,
    EditRequest,
    set_content_image,
)
from app.infra.agent.operations import (
    WRITE_OPS,
    WRITE_OPS_BY_KIND,
    WRITE_OPS_BY_TOOL,
    CreateBannerArgs,
    CreateCampaignArgs,
    CreateContentArgs,
    Ref,
    UpdateBannerArgs,
    UpdateCampaignArgs,
    UpdateContentArgs,
    WriteOp,
    apply_operations,
    build_operation,
    segments_label,
)
from app.infra.campaigns_api import ApiCallError, CampaignsApi
from app.infra.creative_validation import check_banner, check_content
from app.infra.pydantic_errors import map_pydantic_errors
from app.infra.schedule_validation import check_schedule


class NoArgs(BaseModel):
    pass


class CampaignIdArgs(BaseModel):
    campaignId: int


@dataclass(frozen=True)
class ReadTool:
    name: str
    path: str
    description: str
    step: str
    args: type[BaseModel] = NoArgs


READ_TOOLS = [
    ReadTool(
        "list_topics", "/topics", "Справочник тематик (фиксированный enum)", "Смотрю тематики"
    ),
    ReadTool("list_tags", "/tags", "Справочник тегов", "Смотрю теги"),
    ReadTool("list_channels", "/channels", "Каналы: iOS, ANDROID, WEB", "Смотрю каналы"),
    ReadTool(
        "list_banner_types",
        "/banner-types",
        "Типы баннеров с лимитами длины и допустимыми каналами",
        "Смотрю типы баннеров",
    ),
    ReadTool("list_segment_types", "/segment-types", "Типы сегментов", "Смотрю типы сегментов"),
    ReadTool(
        "list_segments",
        "/segments",
        "Сегменты аудитории: код, название, тип, состояние, число клиентов",
        "Ищу сегменты",
    ),
    ReadTool(
        "list_places",
        "/places",
        "Места показа: id, код, описание, defaultBanner, состояние",
        "Подбираю места показа",
    ),
    ReadTool(
        "list_campaigns",
        "/campaigns",
        "Список кампаний: id, название, состояние, даты",
        "Смотрю кампании",
    ),
    ReadTool(
        "get_campaign",
        "/campaigns/{campaignId}",
        "Кампания целиком: шапка, места, сегменты, баннеры, контент, креативы",
        "Открываю кампанию",
        CampaignIdArgs,
    ),
    ReadTool(
        "get_warnings",
        "/campaigns/{campaignId}/warnings",
        "Прогон валидации кампании: ошибки и warnings",
        "Проверяю кампанию",
        CampaignIdArgs,
    ),
    ReadTool(
        "get_audit",
        "/campaigns/{campaignId}/audit",
        "Журнал аудита: правки и переходы, комментарии модератора",
        "Смотрю историю кампании",
        CampaignIdArgs,
    ),
]
READ_TOOLS_BY_NAME = {t.name: t for t in READ_TOOLS}


class WarnArgs(BaseModel):
    message: str = Field(description="Что не так и чем это грозит, по-русски")
    severity: Literal["info", "warning"] = "warning"


class QuestionOption(BaseModel):
    label: str = Field(description="Вариант ответа коротко, 1–5 слов")
    description: str | None = Field(
        None, description="Пояснение под вариантом: что он значит или что будет дальше"
    )
    value: str | None = Field(
        None, description="Текст, который уйдёт в чат при выборе; по умолчанию label"
    )


class Question(BaseModel):
    header: str = Field(description="Тема вопроса в 1–3 слова: «Время начала», «Картинка»")
    question: str = Field(description="Сам вопрос целиком, с вопросительным знаком")
    options: list[QuestionOption] = Field(
        default_factory=list,
        max_length=8,
        description="Варианты ответа. Своё значение пользователь впишет сам: вариант «Другое» не добавляй. "
        "В тексте минимум два варианта; без вариантов и с одним — только в голосовом режиме",
    )
    multiSelect: bool = Field(
        False, description="Можно выбрать несколько вариантов, например сегменты или каналы"
    )


class SuggestArgs(BaseModel):
    # Несколько вопросов за раз: время, место, тема, исключения.
    questions: list[Question] = Field(min_length=1, max_length=5)


class DesignArgs(BaseModel):
    brief: str = Field(
        description="Задача дизайнеру своими словами: продукт, оффер с цифрами, условия, срок, тон, призыв к действию, ссылки из брифа"
    )
    placeId: Ref | None = Field(
        None, description="Место показа: тип баннера берётся из его defaultBanner"
    )
    bannerType: Literal["STORY", "SMART_BANNER"] | None = Field(
        None, description="Явный тип баннера, если место не задано или у него нет defaultBanner"
    )
    channels: list[Literal["iOS", "ANDROID", "WEB"]] | None = Field(
        None, description="Каналы креативов; по умолчанию все допустимые для типа"
    )
    withContent: bool = Field(
        True, description="Нужен ли промо-экран после тапа; у STORY он есть всегда"
    )
    generateImage: bool = Field(
        False, description="Сгенерировать картинку; только если пользователь согласился"
    )
    imageStyle: Literal["pattern", "illustration"] = Field(
        "illustration",
        description="pattern — абстрактный фон-паттерн, тема передаётся цветом; illustration — картинка с предметом по смыслу оффера",
    )
    imageUrl: str | None = Field(
        None, description="Картинка пользователя (https), если он её прислал"
    )
    replaceBannerId: Ref | None = Field(
        None,
        description="Правка готового баннера по id вместо создания нового: дизайнер точечно меняет то, что просили в brief "
        "(тексты, цвета, кнопку, промо-экран), остальное сохраняет",
    )
    redesign: bool = Field(
        False,
        description="Правка: собрать баннер заново с нуля. Только если пользователь просит новый дизайн целиком",
    )
    promoImageOnly: bool = Field(
        False,
        description="Правка: нужна только картинка промо-экрана, баннер не менять. Вместе с replaceBannerId и generateImage",
    )


class ConfirmArgs(BaseModel):
    title: str = Field(
        description="Короткий заголовок шага, например «Создать кампанию «Вклад 16%»»"
    )


class DiscardArgs(BaseModel):
    refs: list[str] | None = Field(
        None, description="Ссылки tmp-N операций, которые убрать; null — очистить весь пакет"
    )


UI_TOOLS: dict[str, tuple[type[BaseModel], str]] = {
    "warn_user": (
        WarnArgs,
        "Показать пользователю предупреждение о спорном или противоречивом решении. Не отказ: после предупреждения продолжай.",
    ),
    "suggest_options": (
        SuggestArgs,
        "Задать пользователю вопросы с вариантами ответа (сегменты, места, даты и т. п.). "
        "К каждому вопросу интерфейс сам добавляет поле для своего ответа",
    ),
    "design_creative": (
        DesignArgs,
        "Поручить дизайн-агенту баннер и промо-экран. Кладёт в пакет баннер, контент и креативы по каналам. "
        "Для нового баннера сначала узнай у пользователя вид картинки: фон-паттерн, иллюстрация или без картинки.",
    ),
    "request_confirmation": (
        ConfirmArgs,
        "Показать пакет пользователю и попросить подтверждение. Записи выполнятся только после «да».",
    ),
    "discard_pending": (DiscardArgs, "Убрать операции из пакета до подтверждения"),
}


def _schema(name: str, description: str, args: type[BaseModel]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": args.model_json_schema(),
        },
    }


def tool_schemas() -> list[dict[str, Any]]:
    schemas = [_schema(t.name, f"{t.description}. GET {t.path}", t.args) for t in READ_TOOLS]
    schemas += [
        _schema(
            op.tool,
            f"{op.description}: кладёт {op.method} {op.path} в пакет на подтверждение",
            op.args,
        )
        for op in WRITE_OPS
    ]
    schemas += [_schema(name, description, args) for name, (args, description) in UI_TOOLS.items()]
    return schemas


STEP_LABELS = {"design_creative": "Дизайнер собирает креатив"}


def step_label(name: str) -> str | None:
    if name in READ_TOOLS_BY_NAME:
        return READ_TOOLS_BY_NAME[name].step
    return STEP_LABELS.get(name)


@dataclass
class ToolContext:
    client: CampaignsApi
    designer: Designer
    campaign_id: int | None
    base: dict[str, Any] | None
    pending: list[dict[str, Any]]
    counter: int
    emit: Callable[[str, dict[str, Any]], None]
    image_mode: Literal["mixed", "ask", "pattern", "illustration"] = "mixed"
    voice: bool = False
    draft_changed: bool = False
    _cache: dict[str, Any] = field(default_factory=dict)

    async def dictionary(self, path: str) -> Any:
        if path not in self._cache:
            self._cache[path] = await self.client.get(path)
        return self._cache[path]

    async def banner_types(self) -> dict[int, dict[str, Any]]:
        return {t["id"]: t for t in await self.dictionary("/banner-types")}

    async def places(self) -> dict[int, dict[str, Any]]:
        return {p["id"]: p for p in await self.dictionary("/places")}

    def next_ref(self) -> str:
        self.counter += 1
        return f"tmp-{self.counter}"

    def current_campaign(self) -> Ref | None:
        if self.campaign_id is not None:
            return self.campaign_id
        return next((op["ref"] for op in self.pending if op["kind"] == "create_campaign"), None)

    def draft(self) -> dict[str, Any] | None:
        return apply_operations(self.base, self.pending)


def _errors_text(errors: list[ApiError]) -> str:
    return "Ошибка проверки, исправь аргументы:\n" + "\n".join(
        f"- {e.code} ({e.field or '—'}): {e.message}" for e in errors
    )


UPDATE_KEYS = {"update_banner": "bannerId", "update_content": "contentId"}


async def _propose(ctx: ToolContext, spec: WriteOp, raw: dict[str, Any]) -> str:
    try:
        args = spec.args.model_validate(raw)
    except ValidationError as exc:
        return _errors_text(map_pydantic_errors(exc.errors()))

    # Иначе человек подтвердит карточку, сервер откажет и придётся подтверждать заново.
    if isinstance(args, (CreateCampaignArgs, UpdateCampaignArgs)):
        campaign = args.campaign
        errors = check_schedule(
            campaign.startDate, campaign.startTime, campaign.endDate, campaign.endTime
        )
        own_id = (
            args.campaignId or ctx.current_campaign()
            if isinstance(args, UpdateCampaignArgs)
            else None
        )
        existing = await ctx.client.get("/campaigns")
        if any(item["name"] == campaign.name and item["id"] != own_id for item in existing):
            errors.append(api_error("NAME_DUPLICATE", "name"))
        if errors:
            return _errors_text(errors)

    # Креатив проверяем до API теми же правилами, что и бэкенд (§6.2).
    if isinstance(args, (CreateBannerArgs, UpdateBannerArgs)):
        banner_type = (await ctx.banner_types()).get(args.banner.bannerTypeId)
        if banner_type is None:
            return f"Ошибка: типа баннера {args.banner.bannerTypeId} нет в справочнике, смотри list_banner_types"
        errors = check_banner(
            args.banner.content,
            type_code=banner_type["code"],
            title_max=banner_type["titleMaxLength"],
            text_max=banner_type["textMaxLength"],
            prefix="banner.content",
            media_base_url=ctx.designer.media_base_url,
        )
        if errors:
            return _errors_text(errors)
    if isinstance(args, (CreateContentArgs, UpdateContentArgs)):
        errors = check_content(
            args.content.content,
            prefix="content.content",
            media_base_url=ctx.designer.media_base_url,
        )
        if errors:
            return _errors_text(errors)

    op = build_operation(
        spec,
        args,
        ref=ctx.next_ref() if spec.creates else None,
        current_campaign=ctx.current_campaign(),
    )
    if spec.kind == "set_segments":
        # В карточке подтверждения пользователь видит названия сегментов, а не коды.
        names = {segment["code"]: segment["name"] for segment in await ctx.dictionary("/segments")}
        op["label"] = segments_label(op["body"], names)
    if "campaignId" in op["params"] and op["params"]["campaignId"] is None:
        return "Ошибка: кампании ещё нет. Сначала propose_create_campaign."
    if spec.kind in UPDATE_KEYS:
        # PUT — полная замена, а новое тело собрано из черновика с прежней правкой: она больше не нужна.
        key = UPDATE_KEYS[spec.kind]
        ctx.pending[:] = [
            p
            for p in ctx.pending
            if not (p["kind"] == spec.kind and p["params"].get(key) == op["params"][key])
        ]
    ctx.pending.append(op)
    ctx.draft_changed = True
    ref = f" Ссылка: {op['ref']}." if op["ref"] else ""
    return f"В пакете: {op['label']}.{ref} Когда шаг собран, вызови request_confirmation."


async def _design(ctx: ToolContext, args: DesignArgs, progress: Callable[[str], None]) -> str:
    banner_types = await ctx.banner_types()
    by_code = {t["code"]: t for t in banner_types.values()}
    draft = ctx.draft() or {}
    previous = (
        next((b for b in draft.get("banners", []) if b["id"] == args.replaceBannerId), None)
        if args.replaceBannerId
        else None
    )
    if args.replaceBannerId and previous is None:
        return f"Ошибка: баннера {args.replaceBannerId} нет в кампании"

    chosen_places = draft.get("places") or []
    if (
        args.placeId is not None
        and previous is None
        and chosen_places
        and args.placeId not in chosen_places
    ):
        # Модель путала похожие места на одном экране и делала креатив под место, которое не выбирали.
        return (
            f"Ошибка: места {args.placeId} нет в кампании, в ней места {', '.join(map(str, chosen_places))}. "
            "Делай креативы только под выбранные места. Если пользователь просил это место, сначала добавь его в кампанию."
        )
    place = (await ctx.places()).get(args.placeId) if isinstance(args.placeId, int) else None
    place_code = place.get("defaultBanner") if place else None
    if args.bannerType and place_code and args.bannerType != place_code:
        return (
            f"Ошибка: место {args.placeId} показывает {place_code}, а не {args.bannerType}. "
            "Передай placeId места нужного типа или не передавай bannerType."
        )

    code: str | None = args.bannerType
    if code is None and previous is not None:
        # Правка: тип у баннера уже есть.
        code = banner_types.get(previous.get("bannerTypeId"), {}).get("code")
    if code is None:
        code = place_code
    if code is None:
        return "Ошибка: не знаю тип баннера. Передай placeId места с defaultBanner или bannerType."
    banner_type = by_code[code]
    channels = args.channels or banner_type["channels"]
    bad = [c for c in channels if c not in banner_type["channels"]]
    if bad:
        return f"Ошибка: {code} не поддерживает каналы {', '.join(bad)}; допустимы {', '.join(banner_type['channels'])}"

    pending_banner = next(
        (op for op in ctx.pending if previous and op["ref"] == args.replaceBannerId), None
    )
    # Промо-экраны, привязанные к переделываемому баннеру через креативы: им тоже нужна новая картинка.
    # Ещё не сохранённые правим прямо в пакете, сохранённым предлагаем update_content.
    linked_contents, saved_contents = [], []
    if pending_banner is not None:
        linked = {
            op["body"].get("contentId")
            for op in ctx.pending
            if op["kind"] == "create_creative"
            and op["body"].get("bannerId") == pending_banner["ref"]
        }
        linked_contents = [
            op for op in ctx.pending if op["kind"] == "create_content" and op["ref"] in linked
        ]
    elif previous:
        linked = {
            c.get("contentId")
            for c in draft.get("creatives", [])
            if c.get("bannerId") == previous["id"]
        }
        saved_contents = [
            c
            for c in draft.get("contents", [])
            if c["id"] in linked and c.get("contentType") == "PROMO"
        ]

    image_style = args.imageStyle if ctx.image_mode == "ask" else ctx.image_mode
    if previous is not None and not args.redesign and not args.promoImageOnly:
        return await _edit_design(
            ctx,
            args,
            previous,
            banner_type,
            pending_banner,
            linked_contents,
            saved_contents,
            image_style,
            progress,
        )

    try:
        outcome = await ctx.designer.design(
            DesignRequest(
                brief=args.brief,
                banner_type=banner_type,
                # §6.1: сторис всегда идёт с PROMO-экраном, даже если модель попросила без него.
                with_content=(args.withContent or code == "STORY") and previous is None,
                generate_image=args.generateImage,
                image_url=args.imageUrl,
                previous=previous,
                content_image=bool(linked_contents or saved_contents) if previous else None,
                promo_only=args.promoImageOnly and previous is not None,
                image_style=image_style,
            ),
            progress,
        )
    except DesignError as exc:
        return f"Ошибка дизайн-агента: {exc}"

    banner_body = {
        "name": outcome.banner_name,
        "bannerTypeId": banner_type["id"],
        "content": outcome.banner,
    }
    lines = [
        f"Баннер {code}: «{outcome.banner.get('title', '')}» — {outcome.banner.get('text', '')}"
    ]
    if pending_banner is not None:
        # Баннер ещё не сохранён: правим операцию в пакете, а не добавляем вторую.
        pending_banner["body"]["content"] = outcome.banner
        if outcome.content_image:
            for op in linked_contents:
                set_content_image(op["body"]["content"], outcome.content_image)
        ctx.draft_changed = True
        lines.append(f"Операция {pending_banner['ref']} в пакете обновлена, дублей нет.")
    elif previous:
        if not args.promoImageOnly:
            lines.append(
                await _propose(
                    ctx,
                    WRITE_OPS_BY_KIND["update_banner"],
                    {"bannerId": args.replaceBannerId, "banner": banner_body},
                )
            )
        if outcome.content_image:
            for saved in saved_contents:
                content = deepcopy(saved["content"])
                set_content_image(content, outcome.content_image)
                body = {
                    "name": saved["name"],
                    "contentType": saved["contentType"],
                    "content": content,
                }
                lines.append(
                    await _propose(
                        ctx,
                        WRITE_OPS_BY_KIND["update_content"],
                        {"contentId": saved["id"], "content": body},
                    )
                )
    else:
        lines.append(
            await _propose(ctx, WRITE_OPS_BY_KIND["create_banner"], {"banner": banner_body})
        )
        banner_ref = (
            ctx.pending[-1]["ref"]
            if ctx.pending and ctx.pending[-1]["kind"] == "create_banner"
            else None
        )
        content_ref = None
        if outcome.content is not None and banner_ref:
            lines.append(
                await _propose(
                    ctx,
                    WRITE_OPS_BY_KIND["create_content"],
                    {
                        "content": {
                            "name": outcome.content_name,
                            "contentType": "PROMO",
                            "content": outcome.content,
                        }
                    },
                )
            )
            content_ref = (
                ctx.pending[-1]["ref"] if ctx.pending[-1]["kind"] == "create_content" else None
            )
        if banner_ref:
            for channel in channels:
                creative = {
                    "name": f"{outcome.banner_name} · {channel}"[:100],
                    "bannerId": banner_ref,
                    "contentId": content_ref,
                    "channelCode": channel,
                }
                lines.append(
                    await _propose(
                        ctx, WRITE_OPS_BY_KIND["create_creative"], {"creative": creative}
                    )
                )
    # Адреса картинок модели не нужны: сравнивая их с черновиком, она решала, что ничего не изменилось.
    image = (outcome.banner.get("image") or {}).get("url")
    previous_image = (((previous or {}).get("content") or {}).get("image") or {}).get("url")
    if image and image != previous_image:
        lines.append("Картинка баннера новая, она уже в превью.")
    elif image:
        lines.append("Картинка баннера прежняя.")
    if outcome.content_image:
        lines.append("Картинка промо-экрана новая, она уже в превью.")
    if args.promoImageOnly and previous and not saved_contents and pending_banner is None:
        lines.append("У этого баннера нет сохранённого промо-экрана: картинку ставить некуда.")
    if ctx.pending:
        lines.append("Правки в пакете и в базу ещё не попали: вызови request_confirmation.")
    lines += outcome.notes
    return "\n".join(lines)


async def _edit_design(
    ctx: ToolContext,
    args: DesignArgs,
    previous: dict[str, Any],
    banner_type: dict[str, Any],
    pending_banner: dict[str, Any] | None,
    linked_contents: list[dict[str, Any]],
    saved_contents: list[dict[str, Any]],
    image_style: Literal["illustration", "pattern", "mixed"],
    progress: Callable[[str], None],
) -> str:
    """Точечная правка готового баннера и его промо-экрана: дизайнер меняет только то, что просили."""
    # У баннера от дизайнера один промо-экран, его и правим вместе с баннером.
    pending_content = linked_contents[0] if linked_contents else None
    saved_content = saved_contents[0] if saved_contents else None
    content = (
        pending_content["body"]["content"]
        if pending_content
        else saved_content["content"]
        if saved_content
        else None
    )
    try:
        outcome = await ctx.designer.edit(
            EditRequest(
                instruction=args.brief,
                banner_type=banner_type,
                banner_name=previous["name"],
                banner=previous["content"],
                content=content,
                generate_image=args.generateImage,
                image_url=args.imageUrl,
                image_style=image_style,
            ),
            progress,
        )
    except DesignError as exc:
        return f"Ошибка дизайн-агента: {exc}"

    banner_changed = (
        outcome.banner != previous["content"] or outcome.banner_name != previous["name"]
    )
    content_changed = content is not None and outcome.content != content
    lines = [
        f"Дизайнер поправил: {outcome.summary or 'правка применена'}",
        f"Баннер: «{outcome.banner.get('title', '')}» — {outcome.banner.get('text', '')}",
    ]
    if not banner_changed and not content_changed:
        lines.append("Креатив не изменился: уточни у пользователя, что именно поменять.")
    elif pending_banner is not None:
        # Баннер ещё не сохранён: правим операции в пакете, а не добавляем вторые.
        pending_banner["body"].update(name=outcome.banner_name, content=outcome.banner)
        if pending_content is not None and content_changed:
            pending_content["body"]["content"] = outcome.content
        ctx.draft_changed = True
        lines.append(f"Операция {pending_banner['ref']} в пакете обновлена, дублей нет.")
    else:
        if banner_changed:
            body = {
                "name": outcome.banner_name,
                "bannerTypeId": banner_type["id"],
                "content": outcome.banner,
            }
            lines.append(
                await _propose(
                    ctx,
                    WRITE_OPS_BY_KIND["update_banner"],
                    {"bannerId": previous["id"], "banner": body},
                )
            )
        if saved_content is not None and content_changed:
            body = {
                "name": saved_content["name"],
                "contentType": saved_content["contentType"],
                "content": outcome.content,
            }
            lines.append(
                await _propose(
                    ctx,
                    WRITE_OPS_BY_KIND["update_content"],
                    {"contentId": saved_content["id"], "content": body},
                )
            )
    if content_changed:
        lines.append("Промо-экран тоже поправлен.")
    image = (outcome.banner.get("image") or {}).get("url")
    if image and image != ((previous["content"].get("image") or {}).get("url")):
        lines.append("Картинка баннера новая, она уже в превью.")
    if outcome.content_image:
        lines.append("Картинка промо-экрана новая, она уже в превью.")
    if ctx.pending:
        lines.append("Правки в пакете и в базу ещё не попали: вызови request_confirmation.")
    lines += outcome.notes
    return "\n".join(lines)


async def run_tool(
    ctx: ToolContext, name: str, raw: dict[str, Any], progress: Callable[[str], None]
) -> str:
    if name in READ_TOOLS_BY_NAME:
        tool = READ_TOOLS_BY_NAME[name]
        try:
            args = tool.args.model_validate(raw)
            result = await ctx.client.get(tool.path.format(**args.model_dump()))
        except ValidationError as exc:
            return _errors_text(map_pydantic_errors(exc.errors()))
        except ApiCallError as exc:
            return f"Ошибка API {exc.status}: {exc}"
        return json.dumps(result, ensure_ascii=False, default=str)

    if name in WRITE_OPS_BY_TOOL:
        return await _propose(ctx, WRITE_OPS_BY_TOOL[name], raw)

    try:
        return await _run_ui_tool(ctx, name, raw, progress)
    except ValidationError as exc:
        # Битые аргументы служебного инструмента возвращаем модели, а не роняем ход.
        return _errors_text(map_pydantic_errors(exc.errors()))


async def _run_ui_tool(
    ctx: ToolContext, name: str, raw: dict[str, Any], progress: Callable[[str], None]
) -> str:
    if name == "warn_user":
        args = WarnArgs.model_validate(raw)
        ctx.emit("warning", args.model_dump())
        return "Предупреждение показано. Продолжай, если пользователь не передумал."
    if name == "suggest_options":
        suggestions = SuggestArgs.model_validate(raw)
        # Голосовая анкета принимает и открытый вопрос, и решение одним вариантом; в тексте это не выбор.
        thin = [q.header for q in suggestions.questions if len(q.options) < 2]
        if thin and not ctx.voice:
            return (
                f"Ошибка: у вопросов {', '.join(thin)} меньше двух вариантов. Вопросы без вариантов "
                "и с одним вариантом работают только в голосовом режиме, добавь варианты."
            )
        questions = [
            {
                "header": q.header,
                "question": q.question,
                "multiSelect": q.multiSelect,
                "options": [
                    {"label": o.label, "value": o.value or o.label, "description": o.description}
                    for o in q.options
                ],
            }
            for q in suggestions.questions
        ]
        ctx.emit("suggestions", {"questions": questions})
        return "Вопросы показаны. Дождись ответа пользователя."
    if name == "discard_pending":
        discard = DiscardArgs.model_validate(raw)
        before = len(ctx.pending)
        ctx.pending[:] = (
            []
            if discard.refs is None
            else [op for op in ctx.pending if op["ref"] not in set(discard.refs)]
        )
        ctx.draft_changed = True
        return (
            f"Убрано операций: {before - len(ctx.pending)}. В пакете осталось: {len(ctx.pending)}."
        )
    if name == "design_creative":
        return await _design(ctx, DesignArgs.model_validate(raw), progress)
    return f"Ошибка: инструмента {name} нет"
