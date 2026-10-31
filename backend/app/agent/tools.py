"""Инструменты чат-агента. JSON-схемы аргументов генерируются из Pydantic-моделей."""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, ValidationError

from app.agent.api_client import ApiCallError, CampaignsApi
from app.agent.designer import Designer, DesignError, DesignRequest, image_aspect_ratio
from app.agent.operations import (
    WRITE_OPS,
    WRITE_OPS_BY_KIND,
    WRITE_OPS_BY_TOOL,
    Ref,
    WriteOp,
    apply_operations,
    build_operation,
    segments_label,
)
from app.domain.creatives import check_banner, check_content
from app.domain.pydantic_errors import map_pydantic_errors


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
    ReadTool("list_topics", "/topics", "Справочник тематик (фиксированный enum)", "Смотрю тематики"),
    ReadTool("list_tags", "/tags", "Справочник тегов", "Смотрю теги"),
    ReadTool("list_channels", "/channels", "Каналы: iOS, ANDROID, WEB", "Смотрю каналы"),
    ReadTool("list_banner_types", "/banner-types", "Типы баннеров с лимитами длины и допустимыми каналами", "Смотрю типы баннеров"),
    ReadTool("list_segment_types", "/segment-types", "Типы сегментов", "Смотрю типы сегментов"),
    ReadTool("list_segments", "/segments", "Сегменты аудитории: код, название, тип, состояние, число клиентов", "Ищу сегменты"),
    ReadTool("list_places", "/places", "Места показа: id, код, описание, defaultBanner, состояние", "Подбираю места показа"),
    ReadTool("list_campaigns", "/campaigns", "Список кампаний: id, название, состояние, даты", "Смотрю кампании"),
    ReadTool("get_campaign", "/campaigns/{campaignId}", "Кампания целиком: шапка, места, сегменты, баннеры, контент, креативы", "Открываю кампанию", CampaignIdArgs),
    ReadTool("get_warnings", "/campaigns/{campaignId}/warnings", "Прогон валидации кампании: ошибки и warnings", "Проверяю кампанию", CampaignIdArgs),
    ReadTool("get_audit", "/campaigns/{campaignId}/audit", "Журнал аудита: правки и переходы, комментарии модератора", "Смотрю историю кампании", CampaignIdArgs),
]
READ_TOOLS_BY_NAME = {t.name: t for t in READ_TOOLS}


class WarnArgs(BaseModel):
    message: str = Field(description="Что не так и чем это грозит, по-русски")
    severity: Literal["info", "warning"] = "warning"


class Suggestion(BaseModel):
    label: str = Field(description="Текст кнопки")
    value: str = Field(description="Текст, который уйдёт в чат при нажатии")
    group: str | None = Field(None, description="Тема вопроса, например «Дата начала». Нужна, только если за раз спрашиваешь о нескольких темах")


class SuggestArgs(BaseModel):
    items: list[Suggestion] = Field(min_length=1, max_length=8)


class DesignArgs(BaseModel):
    brief: str = Field(description="Задача дизайнеру своими словами: продукт, оффер с цифрами, условия, срок, тон, призыв к действию, ссылки из брифа")
    placeId: Ref | None = Field(None, description="Место показа: тип баннера берётся из его defaultBanner")
    bannerType: Literal["STORY", "SMART_BANNER"] | None = Field(None, description="Явный тип баннера, если место не задано или у него нет defaultBanner")
    channels: list[Literal["iOS", "ANDROID", "WEB"]] | None = Field(None, description="Каналы креативов; по умолчанию все допустимые для типа")
    withContent: bool = Field(True, description="Нужен ли промо-экран после тапа")
    generateImage: bool = Field(False, description="Сгенерировать картинку; только если пользователь согласился")
    imageUrl: str | None = Field(None, description="Картинка пользователя (https), если он её прислал")
    replaceBannerId: Ref | None = Field(None, description="Правка: id баннера, который нужно переделать, вместо создания нового")


class ConfirmArgs(BaseModel):
    title: str = Field(description="Короткий заголовок шага, например «Создать кампанию «Вклад 16%»»")


class DiscardArgs(BaseModel):
    refs: list[str] | None = Field(None, description="Ссылки tmp-N операций, которые убрать; null — очистить весь пакет")


UI_TOOLS: dict[str, tuple[type[BaseModel], str]] = {
    "warn_user": (WarnArgs, "Показать пользователю предупреждение о спорном или противоречивом решении. Не отказ: после предупреждения продолжай."),
    "suggest_options": (SuggestArgs, "Показать кнопки-варианты ответа (сегменты, места, даты и т. п.)"),
    "design_creative": (DesignArgs, "Поручить дизайн-агенту баннер и промо-экран. Кладёт в пакет баннер, контент и креативы по каналам."),
    "request_confirmation": (ConfirmArgs, "Показать пакет пользователю и попросить подтверждение. Записи выполнятся только после «да»."),
    "discard_pending": (DiscardArgs, "Убрать операции из пакета до подтверждения"),
}


def _schema(name: str, description: str, args: type[BaseModel]) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": description, "parameters": args.model_json_schema()}}


def tool_schemas() -> list[dict[str, Any]]:
    schemas = [_schema(t.name, f"{t.description}. GET {t.path}", t.args) for t in READ_TOOLS]
    schemas += [_schema(op.tool, f"{op.description}: кладёт {op.method} {op.path} в пакет на подтверждение", op.args) for op in WRITE_OPS]
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


def _errors_text(errors) -> str:
    return "Ошибка проверки, исправь аргументы:\n" + "\n".join(f"- {e.code} ({e.field or '—'}): {e.message}" for e in errors)


async def _propose(ctx: ToolContext, spec: WriteOp, raw: dict[str, Any]) -> str:
    try:
        args = spec.args.model_validate(raw)
    except ValidationError as exc:
        return _errors_text(map_pydantic_errors(exc.errors()))

    # Креатив проверяем до API теми же правилами, что и бэкенд (§6.2).
    if spec.kind in {"create_banner", "update_banner"}:
        banner_type = (await ctx.banner_types()).get(args.banner.bannerTypeId)
        if banner_type is None:
            return f"Ошибка: типа баннера {args.banner.bannerTypeId} нет в справочнике, смотри list_banner_types"
        errors = check_banner(
            args.banner.content,
            type_code=banner_type["code"],
            title_max=banner_type["titleMaxLength"],
            text_max=banner_type["textMaxLength"],
            prefix="banner.content",
        )
        if errors:
            return _errors_text(errors)
    if spec.kind in {"create_content", "update_content"}:
        errors = check_content(args.content.content, prefix="content.content")
        if errors:
            return _errors_text(errors)

    op = build_operation(spec, args, ref=ctx.next_ref() if spec.creates else None, current_campaign=ctx.current_campaign())
    if spec.kind == "set_segments":
        # В карточке подтверждения пользователь видит названия сегментов, а не коды.
        names = {segment["code"]: segment["name"] for segment in await ctx.dictionary("/segments")}
        op["label"] = segments_label(op["body"], names)
    if "campaignId" in op["params"] and op["params"]["campaignId"] is None:
        return "Ошибка: кампании ещё нет. Сначала propose_create_campaign."
    ctx.pending.append(op)
    ctx.draft_changed = True
    ref = f" Ссылка: {op['ref']}." if op["ref"] else ""
    return f"В пакете: {op['label']}.{ref} Когда шаг собран, вызови request_confirmation."


async def _design(ctx: ToolContext, args: DesignArgs, progress: Callable[[str], None]) -> str:
    banner_types = await ctx.banner_types()
    by_code = {t["code"]: t for t in banner_types.values()}
    code = args.bannerType
    if code is None and args.placeId is not None:
        place = (await ctx.places()).get(args.placeId) if isinstance(args.placeId, int) else None
        code = place and place.get("defaultBanner")
    if code is None:
        return "Ошибка: не знаю тип баннера. Передай placeId места с defaultBanner или bannerType."
    banner_type = by_code[code]
    channels = args.channels or banner_type["channels"]
    bad = [c for c in channels if c not in banner_type["channels"]]
    if bad:
        return f"Ошибка: {code} не поддерживает каналы {', '.join(bad)}; допустимы {', '.join(banner_type['channels'])}"

    draft = ctx.draft() or {}
    previous = next((b for b in draft.get("banners", []) if b["id"] == args.replaceBannerId), None) if args.replaceBannerId else None
    if args.replaceBannerId and previous is None:
        return f"Ошибка: баннера {args.replaceBannerId} нет в кампании"

    try:
        outcome = await ctx.designer.design(
            DesignRequest(
                brief=args.brief,
                banner_type=banner_type,
                with_content=args.withContent and previous is None,
                generate_image=args.generateImage,
                image_url=args.imageUrl,
                previous=previous,
            ),
            progress,
        )
    except DesignError as exc:
        return f"Ошибка дизайн-агента: {exc}"

    banner_body = {"name": outcome.banner_name, "bannerTypeId": banner_type["id"], "content": outcome.banner}
    lines = [f"Баннер {code}: «{outcome.banner.get('title', '')}» — {outcome.banner.get('text', '')}"]
    pending_banner = next((op for op in ctx.pending if previous and op["ref"] == args.replaceBannerId), None)
    if pending_banner is not None:
        # Баннер ещё не сохранён: правим операцию в пакете, а не добавляем вторую.
        pending_banner["body"]["content"] = outcome.banner
        image = outcome.banner.get("image")
        linked = {op["body"].get("contentId") for op in ctx.pending if op["kind"] == "create_creative" and op["body"].get("bannerId") == pending_banner["ref"]}
        for op in ctx.pending:
            components = op["body"]["content"]["component"]["components"] if op["kind"] == "create_content" and op["ref"] in linked else None
            if image and components is not None and len(components) < 6 and not any(c["role"] == "image" for c in components):
                components.insert(0, {"role": "image", "url": image["url"], "aspectRatio": image_aspect_ratio(code)})
        ctx.draft_changed = True
        lines.append(f"Операция {pending_banner['ref']} в пакете обновлена, дублей нет.")
    elif previous:
        result = await _propose(ctx, WRITE_OPS_BY_KIND["update_banner"], {"bannerId": args.replaceBannerId, "banner": banner_body})
        lines.append(result)
    else:
        lines.append(await _propose(ctx, WRITE_OPS_BY_KIND["create_banner"], {"banner": banner_body}))
        banner_ref = ctx.pending[-1]["ref"] if ctx.pending and ctx.pending[-1]["kind"] == "create_banner" else None
        content_ref = None
        if outcome.content is not None and banner_ref:
            lines.append(
                await _propose(
                    ctx,
                    WRITE_OPS_BY_KIND["create_content"],
                    {"content": {"name": outcome.content_name, "contentType": "PROMO", "content": outcome.content}},
                )
            )
            content_ref = ctx.pending[-1]["ref"] if ctx.pending[-1]["kind"] == "create_content" else None
        if banner_ref:
            for channel in channels:
                creative = {"name": f"{outcome.banner_name} · {channel}"[:100], "bannerId": banner_ref, "contentId": content_ref, "channelCode": channel}
                lines.append(await _propose(ctx, WRITE_OPS_BY_KIND["create_creative"], {"creative": creative}))
    if outcome.banner.get("image"):
        lines.append(f"Картинка добавлена в баннер и промо-экран: {outcome.banner['image']['url']}")
    lines += outcome.notes
    return "\n".join(lines)


async def run_tool(ctx: ToolContext, name: str, raw: dict[str, Any], progress: Callable[[str], None]) -> str:
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

    if name == "warn_user":
        args = WarnArgs.model_validate(raw)
        ctx.emit("warning", args.model_dump())
        return "Предупреждение показано. Продолжай, если пользователь не передумал."
    if name == "suggest_options":
        args = SuggestArgs.model_validate(raw)
        ctx.emit("suggestions", {"items": [i.model_dump() for i in args.items]})
        return "Кнопки показаны. Дождись ответа пользователя."
    if name == "discard_pending":
        args = DiscardArgs.model_validate(raw)
        before = len(ctx.pending)
        ctx.pending[:] = [] if args.refs is None else [op for op in ctx.pending if op["ref"] not in set(args.refs)]
        ctx.draft_changed = True
        return f"Убрано операций: {before - len(ctx.pending)}. В пакете осталось: {len(ctx.pending)}."
    if name == "design_creative":
        try:
            args = DesignArgs.model_validate(raw)
        except ValidationError as exc:
            return _errors_text(map_pydantic_errors(exc.errors()))
        return await _design(ctx, args, progress)
    return f"Ошибка: инструмента {name} нет"
