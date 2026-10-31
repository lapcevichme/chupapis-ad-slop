"""Перевод ошибок Pydantic в коды каталога `rules.ERRORS`."""

from collections.abc import Iterable, Sequence
from typing import Any

from app.errors import ApiError, api_error

# Поле → код. Словарь различает тип ошибки Pydantic, ключ "*" — для остальных типов.
FIELD_CODES: dict[str, dict[str, str]] = {
    "name": {"missing": "NAME_REQUIRED", "string_too_short": "NAME_REQUIRED", "string_too_long": "NAME_TOO_LONG"},
    "marketingName": {"*": "MARKETING_NAME_TOO_LONG"},
    "startDate": {"missing": "START_DATE_REQUIRED", "*": "DATE_FORMAT_INVALID"},
    "endDate": {"*": "DATE_FORMAT_INVALID"},
    "startTime": {"missing": "START_TIME_REQUIRED", "*": "TIME_FORMAT_INVALID"},
    "endTime": {"*": "TIME_FORMAT_INVALID"},
    "topic": {"missing": "TOPIC_REQUIRED", "*": "TOPIC_INVALID"},
    "tags": {"*": "TAG_INVALID"},
    "keywords": {"*": "KEYWORDS_TOO_LONG"},
    "audienceType": {"missing": "AUDIENCE_TYPE_REQUIRED", "*": "AUDIENCE_TYPE_INVALID"},
    "weight": {"*": "WEIGHT_INVALID"},
    "initialCtr": {"*": "INITIAL_CTR_INVALID"},
    "places": {"missing": "PLACES_REQUIRED", "too_short": "PLACES_REQUIRED", "*": "PLACES_INVALID"},
    "included": {"*": "SEGMENTS_INVALID"},
    "excluded": {"*": "SEGMENTS_INVALID"},
    "bannerTypeId": {"missing": "BANNER_TYPE_REQUIRED", "*": "BANNER_TYPE_INVALID"},
    "actionType": {"missing": "ACTION_TYPE_REQUIRED", "*": "ACTION_TYPE_INVALID"},
    "fontSize": {"*": "FONT_SIZE_INVALID"},
    "fontWeight": {"*": "FONT_WEIGHT_INVALID"},
    "textColor": {"*": "COLOR_INVALID"},
    "color": {"*": "COLOR_INVALID"},
    "backgroundColor": {"*": "COLOR_INVALID"},
    "voiceOver": {"*": "VOICE_OVER_TOO_LONG"},
    "url": {"missing": "IMAGE_URL_REQUIRED", "*": "IMAGE_URL_INVALID"},
    "format": {"missing": "TEXT_FORMAT_REQUIRED", "*": "TEXT_FORMAT_INVALID"},
    "axis": {"*": "CONTENT_AXIS_INVALID"},
    "components": {"*": "CONTENT_COMPONENTS_COUNT"},
    "role": {"*": "CONTENT_ROLE_INVALID"},
    "contentType": {"*": "CONTENT_TYPE_INVALID"},
    "bannerId": {"missing": "BANNER_REQUIRED", "*": "FIELD_INVALID"},
    "channelCode": {"missing": "CHANNEL_REQUIRED", "*": "FIELD_INVALID"},
    "comment": {"*": "DECLINE_COMMENT_REQUIRED"},
    "code": {"*": "PLACE_CODE_REQUIRED"},
    "description": {"*": "PLACE_DESCRIPTION_REQUIRED"},
}


def _field_path(loc: Sequence[Any]) -> str:
    path = ""
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)
    return path


def _code_for(loc: Sequence[Any], error_type: str, fallback: str) -> str:
    if error_type == "extra_forbidden":
        return "UNKNOWN_FIELD"
    if error_type == "json_invalid":
        return "JSON_INVALID"
    if error_type.startswith("union_tag"):
        return "CONTENT_ROLE_INVALID"
    # Ищем ближайшее к ошибке известное поле: у topic.value ошибка относится к topic.
    for part in reversed(loc):
        if isinstance(part, str) and part in FIELD_CODES:
            codes = FIELD_CODES[part]
            return codes.get(error_type, codes.get("*", fallback))
    return fallback


def _message(code: str, error: dict[str, Any]) -> str:
    from app.domain.rules import ERRORS

    base = ERRORS[code]
    if code in {"UNKNOWN_FIELD", "FIELD_INVALID", "BANNER_SCHEMA_INVALID", "CONTENT_SCHEMA_INVALID"}:
        return f"{base}: {error.get('msg', '')}"
    return base


def map_pydantic_errors(
    errors: Iterable[dict[str, Any]], *, strip: int = 0, prefix: str | None = None, fallback: str = "FIELD_INVALID"
) -> list[ApiError]:
    """`strip` отрезает служебную голову loc (например, "body"), `prefix` дописывает путь спереди."""
    result: list[ApiError] = []
    for error in errors:
        loc = list(error.get("loc", ()))[strip:]
        # Pydantic вставляет тег дискриминатора в путь: components[0].text.format → components[0].format.
        loc = [part for i, part in enumerate(loc) if not (i > 0 and isinstance(loc[i - 1], int) and part in {"text", "image", "button"})]
        code = _code_for(loc, error.get("type", ""), fallback)
        field = _field_path(loc)
        if prefix:
            field = f"{prefix}.{field}" if field else prefix
        result.append(api_error(code, field or None, _message(code, error)))
    return result
