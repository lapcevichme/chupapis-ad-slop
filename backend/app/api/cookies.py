from typing import Any

from fastapi import Response

from app.core.config import Settings
from app.domain.auth import IssuedTokens

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"


def _common(settings: Settings) -> dict[str, Any]:
    return {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "domain": settings.cookie_domain or None,
    }


def set_auth_cookies(response: Response, tokens: IssuedTokens, settings: Settings) -> None:
    # Refresh-токен нужен только эндпоинтам /auth, поэтому браузер не шлёт его никуда больше.
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_ttl,
        httponly=True,
        path=settings.refresh_cookie_path,
        **_common(settings),
    )
    # Читается из JS намеренно: SPA повторяет значение в X-CSRF-Token (double-submit cookie).
    response.set_cookie(
        CSRF_COOKIE,
        tokens.csrf_token,
        max_age=settings.refresh_ttl,
        httponly=False,
        path="/",
        **_common(settings),
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_COOKIE, path=settings.refresh_cookie_path, httponly=True, **_common(settings)
    )
    response.delete_cookie(CSRF_COOKIE, path="/", **_common(settings))


def clearing_headers(settings: Settings) -> list[tuple[str, str]]:
    """Заголовки Set-Cookie, сбрасывающие обе cookie, для ответа с ошибкой."""
    response = Response()
    clear_auth_cookies(response, settings)
    return [("set-cookie", value) for key, value in response.headers.items() if key == "set-cookie"]
