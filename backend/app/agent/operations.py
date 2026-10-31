"""Пишущие операции агента: каталог `propose_*`, черновик и выполнение пакета после подтверждения.

Каждый `propose_*` соответствует одному пишущему вызову API §3. Модель только кладёт операцию в пакет,
вызывает API узел подтверждения графа (`graph.confirm_node`), и только после «да» пользователя.
"""

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from app.agent.api_client import ApiCallError, CampaignsApi
from app.schemas import api

def _normalize_ref(value: Any) -> Any:
    # Модели иногда присылают id строкой или в лишних кавычках: '"tmp-2"', "101".
    if isinstance(value, str):
        value = value.strip().strip("\"'")
        if value.isdigit():
            return int(value)
    return value


# Ссылка на сущность: настоящий id или временный "tmp-N" для того, что создаётся в этом же пакете.
Ref = Annotated[int | str, BeforeValidator(_normalize_ref)]
TMP_REF = re.compile(r"^tmp-\d+$")


class RefItem(BaseModel):
    value: Ref
    label: str | None = None


class ProposedCampaign(api.CampaignInfo):
    tags: list[RefItem] = Field(default_factory=list, description="Теги: id из list_tags или tmp-N нового тега")
    places: list[RefItem] = Field(min_length=1, description="Места показа: id из list_places или tmp-N нового места")


class ProposedCreative(api.CreativeCreate):
    bannerId: Ref
    contentId: Ref | None = None


CAMPAIGN_ID = Field(None, description="id кампании или tmp-N; по умолчанию текущая кампания диалога")


class CampaignArgs(BaseModel):
    campaignId: Ref | None = CAMPAIGN_ID


class CreateCampaignArgs(BaseModel):
    campaign: ProposedCampaign


class UpdateCampaignArgs(CampaignArgs):
    campaign: ProposedCampaign = Field(description="Полная шапка: PUT заменяет объект целиком")


class SegmentsArgs(CampaignArgs):
    included: list[str] = Field(default_factory=list, description="Коды сегментов включения (OR)")
    excluded: list[str] = Field(default_factory=list, description="Коды сегментов исключения")


class CreateBannerArgs(CampaignArgs):
    banner: api.BannerCreate


class UpdateBannerArgs(CreateBannerArgs):
    bannerId: Ref


class BannerRefArgs(CampaignArgs):
    bannerId: Ref


class CreateContentArgs(CampaignArgs):
    content: api.ContentCreate


class UpdateContentArgs(CreateContentArgs):
    contentId: Ref


class ContentRefArgs(CampaignArgs):
    contentId: Ref


class CreateCreativeArgs(CampaignArgs):
    creative: ProposedCreative


class UpdateCreativeArgs(CreateCreativeArgs):
    creativeId: Ref


class CreativeRefArgs(CampaignArgs):
    creativeId: Ref


class CreatePlaceArgs(BaseModel):
    place: api.PlaceCreate


class CreateTagArgs(BaseModel):
    tag: api.TagCreate


class DeclineArgs(CampaignArgs):
    comment: str = Field(description="Комментарий модератора, обязателен")


@dataclass(frozen=True)
class WriteOp:
    tool: str
    kind: str
    method: str
    path: str
    args: type[BaseModel]
    description: str
    body: str | None = None  # поле аргументов, которое уходит телом запроса
    creates: bool = False


WRITE_OPS: list[WriteOp] = [
    WriteOp("propose_create_campaign", "create_campaign", "POST", "/campaigns", CreateCampaignArgs, "Создать кампанию (DRAFT)", "campaign", True),
    WriteOp("propose_update_campaign", "update_campaign", "PUT", "/campaigns/{campaignId}", UpdateCampaignArgs, "Заменить шапку и места кампании", "campaign"),
    WriteOp("propose_delete_campaign", "delete_campaign", "DELETE", "/campaigns/{campaignId}", CampaignArgs, "Удалить кампанию (только DRAFT/NEEDS_WORK без показа)"),
    WriteOp("propose_set_segments", "set_segments", "PUT", "/campaigns/{campaignId}/segments", SegmentsArgs, "Задать сегменты включения и исключения"),
    WriteOp("propose_create_banner", "create_banner", "POST", "/campaigns/{campaignId}/banners", CreateBannerArgs, "Создать баннер", "banner", True),
    WriteOp("propose_update_banner", "update_banner", "PUT", "/campaigns/{campaignId}/banners/{bannerId}", UpdateBannerArgs, "Заменить баннер", "banner"),
    WriteOp("propose_delete_banner", "delete_banner", "DELETE", "/campaigns/{campaignId}/banners/{bannerId}", BannerRefArgs, "Удалить баннер"),
    WriteOp("propose_create_content", "create_content", "POST", "/campaigns/{campaignId}/contents", CreateContentArgs, "Создать PROMO-контент", "content", True),
    WriteOp("propose_update_content", "update_content", "PUT", "/campaigns/{campaignId}/contents/{contentId}", UpdateContentArgs, "Заменить контент", "content"),
    WriteOp("propose_delete_content", "delete_content", "DELETE", "/campaigns/{campaignId}/contents/{contentId}", ContentRefArgs, "Удалить контент"),
    WriteOp("propose_create_creative", "create_creative", "POST", "/campaigns/{campaignId}/creatives", CreateCreativeArgs, "Создать креатив: баннер + контент + канал", "creative", True),
    WriteOp("propose_update_creative", "update_creative", "PUT", "/campaigns/{campaignId}/creatives/{creativeId}", UpdateCreativeArgs, "Заменить креатив", "creative"),
    WriteOp("propose_delete_creative", "delete_creative", "DELETE", "/campaigns/{campaignId}/creatives/{creativeId}", CreativeRefArgs, "Удалить креатив"),
    WriteOp("propose_create_place", "create_place", "POST", "/places", CreatePlaceArgs, "Создать место показа в справочнике", "place", True),
    WriteOp("propose_create_tag", "create_tag", "POST", "/tags", CreateTagArgs, "Создать тег в справочнике", "tag", True),
    WriteOp("propose_to_moderation", "to_moderation", "POST", "/campaigns/{campaignId}/to-moderation", CampaignArgs, "Отправить на модерацию"),
    WriteOp("propose_decline", "decline", "POST", "/campaigns/{campaignId}/decline", DeclineArgs, "Отклонить (роль модератора)"),
    WriteOp("propose_approve", "approve", "POST", "/campaigns/{campaignId}/approve", CampaignArgs, "Одобрить (роль модератора)"),
    WriteOp("propose_activate", "activate", "POST", "/campaigns/{campaignId}/activate", CampaignArgs, "Активировать одобренную кампанию"),
    WriteOp("propose_stop", "stop", "POST", "/campaigns/{campaignId}/stop", CampaignArgs, "Остановить показ"),
]
WRITE_OPS_BY_TOOL = {op.tool: op for op in WRITE_OPS}
WRITE_OPS_BY_KIND = {op.kind: op for op in WRITE_OPS}


def build_operation(spec: WriteOp, args: BaseModel, *, ref: str | None, current_campaign: Ref | None) -> dict[str, Any]:
    params = args.model_dump(mode="json", exclude_none=True)
    if "campaignId" in type(args).model_fields:
        params["campaignId"] = params.get("campaignId", current_campaign)
    if spec.body:
        body = params.pop(spec.body)
    elif spec.kind == "set_segments":
        body = {"included": params.pop("included", []), "excluded": params.pop("excluded", [])}
    elif spec.kind == "decline":
        body = {"comment": params.pop("comment")}
    else:
        body = None
    return {"ref": ref, "kind": spec.kind, "params": params, "body": body, "label": op_label(spec.kind, body, params)}


def segments_label(body: dict[str, Any], names: dict[str, str]) -> str:
    """«Сегменты: включить Москва, Возраст 26–45; исключить —». Без справочника — коды."""

    def join(codes: list[str]) -> str:
        return ", ".join(names.get(code, code) for code in codes) or "—"

    return f"Сегменты: включить {join(body['included'])}; исключить {join(body['excluded'])}"


def op_label(kind: str, body: Any, params: dict[str, Any]) -> str:
    b = body or {}
    match kind:
        case "create_campaign":
            return f"Создать кампанию «{b.get('name')}»"
        case "update_campaign":
            return f"Обновить шапку кампании «{b.get('name')}»"
        case "set_segments":
            return segments_label(b, {})
        case "create_banner" | "update_banner":
            action = "Создать" if kind.startswith("create") else "Заменить"
            kind_name = {1: "STORY", 2: "SMART_BANNER"}.get(b.get("bannerTypeId"), "")
            return f"{action} баннер {kind_name} «{b.get('name')}»".replace("  ", " ")
        case "create_content" | "update_content":
            return f"{'Создать' if kind.startswith('create') else 'Заменить'} промо-экран «{b.get('name')}»"
        case "create_creative" | "update_creative":
            return f"{'Создать' if kind.startswith('create') else 'Заменить'} креатив «{b.get('name')}» для {b.get('channelCode')}"
        case "create_place":
            return f"Создать место показа {b.get('code')} «{b.get('description')}»"
        case "create_tag":
            return f"Создать тег «{b.get('name')}»"
        case "decline":
            return f"Отклонить кампанию: {b.get('comment')}"
    labels = {
        "delete_campaign": "Удалить кампанию",
        "delete_banner": f"Удалить баннер {params.get('bannerId')}",
        "delete_content": f"Удалить контент {params.get('contentId')}",
        "delete_creative": f"Удалить креатив {params.get('creativeId')}",
        "to_moderation": "Отправить кампанию на модерацию",
        "approve": "Одобрить кампанию",
        "activate": "Активировать кампанию: показ начнётся у клиентов",
        "stop": "Остановить показ кампании",
    }
    return labels[kind]


# --- Черновик


EMPTY_DRAFT: dict[str, Any] = {
    "places": [],
    "tags": [],
    "segments": {"included": [], "excluded": []},
    "banners": [],
    "contents": [],
    "creatives": [],
}
SERVER_FIELDS = ("id", "state", "published", "author", "lastEditAuthor")


def _header_from_info(body: dict[str, Any]) -> dict[str, Any]:
    header = {k: v for k, v in body.items() if k not in {"topic", "tags", "places"}}
    header["topic"] = body["topic"]["value"]
    header["tags"] = [t["value"] for t in body.get("tags", [])]
    header["places"] = [p["value"] for p in body["places"]]
    header.setdefault("weight", 0.0)
    header.setdefault("initialCtr", 15.0)
    return header


def _replace(items: list[dict], item_id: Ref, new: dict | None) -> list[dict]:
    result = []
    for item in items:
        if item["id"] == item_id:
            if new is not None:
                result.append(new)
        else:
            result.append(item)
    return result


def apply_operations(base: dict[str, Any] | None, pending: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Черновик = кампания из API (или пустая) + ещё не подтверждённые операции. Лишь для превью."""
    if base is None and not any(op["kind"] == "create_campaign" for op in pending):
        return None
    draft = deepcopy(base) if base else deepcopy(EMPTY_DRAFT)
    for op in pending:
        body, params, kind = op["body"], op["params"], op["kind"]
        match kind:
            case "create_campaign" | "update_campaign":
                draft |= _header_from_info(body)
            case "set_segments":
                draft["segments"] = body
            case "create_banner" | "create_content" | "create_creative":
                collection = {"create_banner": "banners", "create_content": "contents", "create_creative": "creatives"}[kind]
                draft[collection].append({"id": op["ref"], "campaignId": params.get("campaignId"), **body})
            case "update_banner" | "update_content" | "update_creative":
                collection, key = {"update_banner": ("banners", "bannerId"), "update_content": ("contents", "contentId"), "update_creative": ("creatives", "creativeId")}[kind]
                draft[collection] = _replace(draft[collection], params[key], {"id": params[key], "campaignId": params.get("campaignId"), **body})
            case "delete_banner" | "delete_content" | "delete_creative":
                collection, key = {"delete_banner": ("banners", "bannerId"), "delete_content": ("contents", "contentId"), "delete_creative": ("creatives", "creativeId")}[kind]
                draft[collection] = _replace(draft[collection], params[key], None)
    return draft


def public_draft(draft: dict[str, Any] | None) -> dict[str, Any] | None:
    if draft is None:
        return None
    return {k: v for k, v in draft.items() if k not in SERVER_FIELDS}


def draft_warnings(draft: dict[str, Any] | None, places: dict[int, dict], banner_types: dict[int, dict]) -> list[str]:
    """Те же правила, что у GET /warnings (§4, §7.2 mock-data), но по черновику до сохранения."""
    from app.domain.rules import WARNINGS

    if not draft:
        return []
    used_places = [places[p] for p in draft.get("places", []) if p in places]
    banner_codes = {b["id"]: banner_types.get(b.get("bannerTypeId"), {}).get("code") for b in draft.get("banners", [])}
    creative_codes = {banner_codes.get(c.get("bannerId")) for c in draft.get("creatives", [])}
    warnings = []
    if any(p.get("defaultBanner") and p["defaultBanner"] not in creative_codes for p in used_places):
        warnings.append(WARNINGS["PLACE_NO_CREATIVE"])
    if any(p.get("state") == "INACTIVE" for p in used_places):
        warnings.append(WARNINGS["PLACE_INACTIVE"])
    if not draft.get("tags"):
        warnings.append(WARNINGS["TAGS_MISSING"])
    return warnings


# --- Сводка для подтверждения

FIELD_LABELS = {
    "name": "Название",
    "marketingName": "Маркетинговое название",
    "startDate": "Дата начала",
    "startTime": "Время начала",
    "endDate": "Дата окончания",
    "endTime": "Время окончания",
    "topic": "Тематика",
    "tags": "Теги",
    "keywords": "Ключевые слова",
    "audienceType": "Аудитория",
    "weight": "Вес",
    "initialCtr": "Начальный CTR",
    "places": "Места показа",
    "segments.included": "Сегменты включения",
    "segments.excluded": "Сегменты исключения",
}


def confirmation_changes(base: dict[str, Any] | None, pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
    before = base or {}
    after = apply_operations(base, pending) or {}
    changes = []
    for field, label in FIELD_LABELS.items():
        if "." in field:
            group, key = field.split(".")
            old, new = (before.get(group) or {}).get(key), (after.get(group) or {}).get(key)
            old, new = old or None, new or None
        else:
            old, new = before.get(field), after.get(field)
        if old != new:
            changes.append({"field": field, "label": label, "from": old, "to": new})
    return changes


# --- Выполнение


def _resolve(value: Any, id_map: dict[str, int]) -> Any:
    if isinstance(value, str) and TMP_REF.match(value):
        if value not in id_map:
            raise KeyError(value)
        return id_map[value]
    if isinstance(value, dict):
        return {k: _resolve(v, id_map) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, id_map) for v in value]
    return value


@dataclass
class ExecutionResult:
    done: list[str]
    error: str | None
    campaign_id: int | None
    id_map: dict[str, int]


async def execute(pending: list[dict[str, Any]], client: CampaignsApi, *, campaign_id: int | None, id_map: dict[str, int]) -> ExecutionResult:
    """Выполняет пакет по порядку и останавливается на первой ошибке API."""
    id_map = dict(id_map)
    done: list[str] = []
    for op in pending:
        spec = WRITE_OPS_BY_KIND[op["kind"]]
        try:
            params = _resolve(op["params"], id_map)
            body = _resolve(op["body"], id_map)
        except KeyError as missing:
            return ExecutionResult(done, f"«{op['label']}»: ссылка {missing} не создана в этом пакете", campaign_id, id_map)
        if "campaignId" in params and params["campaignId"] is None:
            return ExecutionResult(done, f"«{op['label']}»: кампания ещё не создана", campaign_id, id_map)
        try:
            response = await client.request(spec.method, spec.path.format(**params), body)
        except ApiCallError as exc:
            details = "; ".join(f"{e.get('code')} ({e.get('field') or '—'}): {e.get('message')}" for e in exc.errors)
            return ExecutionResult(done, f"«{op['label']}» → HTTP {exc.status}: {details}", campaign_id, id_map)
        if op["ref"] and isinstance(response, dict) and "id" in response:
            id_map[op["ref"]] = response["id"]
        if spec.kind == "create_campaign":
            campaign_id = response["id"]
        elif spec.kind == "delete_campaign":
            campaign_id = None
        suffix = f" → id {response['id']}" if op["ref"] and isinstance(response, dict) and "id" in response else ""
        state = f", состояние {response['state']}" if isinstance(response, dict) and "state" in response else ""
        done.append(f"{op['label']}{suffix}{state}")
    return ExecutionResult(done, None, campaign_id, id_map)
