from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.cookies import REFRESH_COOKIE, clear_auth_cookies, clearing_headers, set_auth_cookies
from app.api.deps import (
    ERROR_RESPONSES,
    AuthServiceDep,
    ClientDep,
    CurrentUserDep,
    SettingsDep,
    UserAgentDep,
    rate_limit,
)
from app.api.schemas.auth import LoginRequest, RegisterRequest, TokenPair
from app.core.config import Settings
from app.core.errors import DomainError, unauthorized
from app.domain.auth import ClientKind, IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)

_refresh_bearer = HTTPBearer(
    auto_error=False, description="Mobile clients send the refresh token as Bearer"
)
RefreshBearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_refresh_bearer)]
RefreshCookieDep = Annotated[str | None, Cookie(alias=REFRESH_COOKIE, include_in_schema=False)]


def _token_pair(
    response: Response, tokens: IssuedTokens, client: ClientKind, settings: Settings
) -> TokenPair:
    if client is ClientKind.WEB:
        set_auth_cookies(response, tokens, settings)
        return TokenPair(access_token=tokens.access_token, expires_in=tokens.expires_in)
    return TokenPair(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    path="/register",
    status_code=status.HTTP_201_CREATED,
    summary="Создать аккаунт менеджера и войти",
    dependencies=[Depends(rate_limit("register"))],
)
async def register(
    payload: RegisterRequest,
    response: Response,
    svc: AuthServiceDep,
    client: ClientDep,
    user_agent: UserAgentDep,
    settings: SettingsDep,
) -> TokenPair:
    tokens = await svc.register(
        email=payload.email,
        password=payload.password,
        username=payload.username,
        client=client,
        user_agent=user_agent,
    )
    return _token_pair(response, tokens, client, settings)


@router.post(
    path="/login",
    summary="Войти по почте и паролю",
    dependencies=[Depends(rate_limit("login"))],
)
async def login(
    payload: LoginRequest,
    response: Response,
    svc: AuthServiceDep,
    client: ClientDep,
    user_agent: UserAgentDep,
    settings: SettingsDep,
) -> TokenPair:
    tokens = await svc.login(
        email=payload.email, password=payload.password, client=client, user_agent=user_agent
    )
    return _token_pair(response, tokens, client, settings)


@router.post(
    path="/refresh",
    summary="Обновить access-токен и повернуть refresh-токен",
    dependencies=[Depends(rate_limit("refresh"))],
)
async def refresh(
    response: Response,
    svc: AuthServiceDep,
    settings: SettingsDep,
    bearer: RefreshBearerDep,
    refresh_cookie: RefreshCookieDep = None,
    csrf_token: Annotated[
        str | None, Header(alias="X-CSRF-Token", description="Browsers only: the csrf_token cookie")
    ] = None,
) -> TokenPair:
    if refresh_cookie:
        try:
            tokens = await svc.refresh(refresh_cookie, csrf_token=csrf_token)
        except DomainError as exc:
            if exc.status_code == 401:
                exc.headers.extend(clearing_headers(settings))
            raise
        return _token_pair(response, tokens, ClientKind.WEB, settings)

    if bearer is None:
        raise unauthorized("INVALID_TOKEN", "Токен обновления не передан")
    tokens = await svc.refresh(bearer.credentials, csrf_token=None)
    return _token_pair(response, tokens, ClientKind.MOBILE, settings)


@router.post(
    path="/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Завершить текущую сессию (идемпотентно)",
)
async def logout(
    response: Response,
    svc: AuthServiceDep,
    settings: SettingsDep,
    bearer: RefreshBearerDep,
    refresh_cookie: RefreshCookieDep = None,
) -> None:
    raw_token = refresh_cookie or (bearer.credentials if bearer else None)
    if raw_token:
        # Это не refresh-токен (например, access-токен веб-клиента): отзывать нечего.
        with suppress(DomainError):
            await svc.logout(raw_token)
    clear_auth_cookies(response, settings)


@router.post(
    path="/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Завершить все сессии пользователя и отозвать выданные токены",
)
async def logout_all(
    user: CurrentUserDep,
    response: Response,
    svc: AuthServiceDep,
    settings: SettingsDep,
) -> None:
    await svc.logout_everywhere(user.id)
    clear_auth_cookies(response, settings)
