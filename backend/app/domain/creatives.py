"""Проверка JSON баннера и контента: схема плюс правила, которых нет в самой схеме.

Функции не ходят в БД, поэтому их же вызывает агент перед отправкой креатива в API.
"""

from typing import Any

from pydantic import ValidationError

from app.config import settings
from app.domain.enums import ActionType
from app.domain.pydantic_errors import map_pydantic_errors
from app.errors import ApiError, api_error
from app.schemas.creative_json import ActionLink, BannerContent, PromoButton, PromoContent, PromoImage

LINK_REQUIRED_ACTIONS = {ActionType.EXTERNAL_LINK, ActionType.OPEN_SMART_LINK}
LINK_FORBIDDEN_ACTIONS = {ActionType.CLOSE_CAMPAIGN, ActionType.DONE_CAMPAIGN}


def _has_link(link: ActionLink | None) -> bool:
    return link is not None and any([link.iOS, link.android, link.web])


def check_link(action_type: ActionType, link: ActionLink | None, field: str) -> list[ApiError]:
    if action_type in LINK_REQUIRED_ACTIONS and not _has_link(link):
        return [api_error("LINK_REQUIRED", field, f"Для actionType={action_type} нужна ссылка хотя бы для одной платформы")]
    if action_type in LINK_FORBIDDEN_ACTIONS and link is not None:
        return [api_error("LINK_FORBIDDEN", field, f"Для actionType={action_type} ссылка запрещена, уберите link")]
    return []


def check_image_url(url: str, field: str) -> list[ApiError]:
    if url.startswith("https://") or url.startswith(settings.media_base_url):
        return []
    return [api_error("IMAGE_URL_INVALID", field)]


def check_banner(
    content: BannerContent, *, type_code: str, title_max: int, text_max: int, prefix: str = "content"
) -> list[ApiError]:
    errors: list[ApiError] = []
    if content.title is not None and len(content.title) > title_max:
        errors.append(
            api_error(
                "BANNER_TITLE_TOO_LONG",
                f"{prefix}.title",
                f"Заголовок {len(content.title)} символов, лимит для {type_code} — {title_max}",
            )
        )
    if content.text is not None and len(content.text) > text_max:
        errors.append(
            api_error(
                "BANNER_TEXT_TOO_LONG",
                f"{prefix}.text",
                f"Текст {len(content.text)} символов, лимит для {type_code} — {text_max}",
            )
        )
    errors += check_link(content.actionType, content.link, f"{prefix}.link")
    if content.image is not None:
        errors += check_image_url(content.image.url, f"{prefix}.image.url")
    return errors


def check_content(content: PromoContent, *, prefix: str = "content") -> list[ApiError]:
    errors: list[ApiError] = []
    for index, component in enumerate(content.component.components):
        field = f"{prefix}.component.components[{index}]"
        if isinstance(component, PromoButton):
            errors += check_link(component.actionType, component.link, f"{field}.link")
        elif isinstance(component, PromoImage):
            errors += check_image_url(component.url, f"{field}.url")
    return errors


def validate_banner_json(
    raw: Any, *, type_code: str, title_max: int, text_max: int, prefix: str = "content"
) -> tuple[BannerContent | None, list[ApiError]]:
    try:
        content = BannerContent.model_validate(raw)
    except ValidationError as exc:
        return None, map_pydantic_errors(exc.errors(), prefix=prefix, fallback="BANNER_SCHEMA_INVALID")
    return content, check_banner(content, type_code=type_code, title_max=title_max, text_max=text_max, prefix=prefix)


def validate_content_json(raw: Any, *, prefix: str = "content") -> tuple[PromoContent | None, list[ApiError]]:
    try:
        content = PromoContent.model_validate(raw)
    except ValidationError as exc:
        return None, map_pydantic_errors(exc.errors(), prefix=prefix, fallback="CONTENT_SCHEMA_INVALID")
    return content, check_content(content, prefix=prefix)
