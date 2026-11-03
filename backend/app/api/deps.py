from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import timedelta
from typing import Annotated, Any, Literal

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

from app.contracts.errors import ErrorResponse
from app.core.config import Settings
from app.core.errors import fail, unauthorized
from app.core.security.tokens import TokenCodec
from app.db.database import Database
from app.db.uow import UnitOfWork
from app.domain.auth import ClientKind
from app.domain.users import CurrentUser, Permission, ensure_can
from app.infra.rate_limit import RateLimiter
from app.infra.storage import ObjectStorage
from app.service.auth import AuthService, resolve_current_user
from app.service.campaigns import CampaignService
from app.service.children import CreativeService
from app.service.dictionaries import DictionaryService
from app.service.media import MediaService, MediaStore, StudioService

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Ошибки валидации или жизненного цикла"},
    401: {"model": ErrorResponse, "description": "Нужно войти (NOT_AUTHENTICATED, TOKEN_EXPIRED)"},
    403: {"model": ErrorResponse, "description": "ROLE_FORBIDDEN"},
    404: {"model": ErrorResponse, "description": "ENTITY_NOT_FOUND"},
}

# Всё долгоживущее создаётся один раз в фабрике приложения и читается из app.state:
# так тест собирает приложение со своими настройками и подменами.


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _database(request: Request) -> Database:
    database: Database = request.app.state.db
    return database


def _redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


def _storage(request: Request) -> ObjectStorage:
    storage: ObjectStorage = request.app.state.storage
    return storage


def _media_store(request: Request) -> MediaStore:
    store: MediaStore = request.app.state.media_store
    return store


def _codec(request: Request) -> TokenCodec:
    codec: TokenCodec = request.app.state.token_codec
    return codec


SettingsDep = Annotated[Settings, Depends(_settings)]
DatabaseDep = Annotated[Database, Depends(_database)]
RedisDep = Annotated[Redis, Depends(_redis)]
StorageDep = Annotated[ObjectStorage, Depends(_storage)]
MediaStoreDep = Annotated[MediaStore, Depends(_media_store)]
CodecDep = Annotated[TokenCodec, Depends(_codec)]


async def _unit_of_work(db: DatabaseDep) -> AsyncIterator[UnitOfWork]:
    async with db.unit_of_work() as uow:
        yield uow


# scope="function": коммит идёт до отправки ответа, поэтому упавший коммит даёт честный 500,
# а не 200 для данных, которые не сохранились.
UowDep = Annotated[UnitOfWork, Depends(_unit_of_work, scope="function")]

_bearer = HTTPBearer(auto_error=False, description="Access-токен из /auth/login или /auth/refresh")
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


async def current_user(creds: BearerDep, codec: CodecDep, uow: UowDep) -> CurrentUser:
    if creds is None:
        raise unauthorized()
    return await resolve_current_user(uow, codec.decode_access(creds.credentials))


CurrentUserDep = Annotated[CurrentUser, Depends(current_user)]


def bearer_token(creds: BearerDep) -> str:
    """Сырой access-токен запроса: агент ходит в API кампаний от имени этого же пользователя."""
    if creds is None:
        raise unauthorized()
    return creds.credentials


TokenDep = Annotated[str, Depends(bearer_token)]


def require(permission: Permission) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    async def dependency(user: CurrentUserDep) -> CurrentUser:
        ensure_can(user, permission)
        return user

    return dependency


def rate_limit(bucket: str) -> Callable[[Request, RedisDep, SettingsDep], Awaitable[None]]:
    """По IP клиента. За прокси запускайте uvicorn с --proxy-headers, чтобы IP был настоящим."""

    async def dependency(request: Request, redis: RedisDep, settings: SettingsDep) -> None:
        if not settings.rate_limit_enabled:
            return
        limiter = RateLimiter(redis, limit=settings.auth_rate_limit_per_minute, window_sec=60)
        client = request.client.host if request.client else "unknown"
        if not await limiter.hit(f"{bucket}:{client}"):
            raise fail("RATE_LIMITED", status=429)

    return dependency


def _client_kind(
    x_client: Annotated[Literal["web", "mobile"], Header(alias="X-Client")] = "web",
) -> ClientKind:
    return ClientKind(x_client)


ClientDep = Annotated[ClientKind, Depends(_client_kind)]
UserAgentDep = Annotated[str | None, Header(alias="User-Agent", include_in_schema=False)]


def _auth_service(uow: UowDep, codec: CodecDep, settings: SettingsDep) -> AuthService:
    return AuthService(
        uow,
        codec,
        refresh_ttl=timedelta(seconds=settings.refresh_ttl),
        registration_enabled=settings.registration_enabled,
    )


def _campaign_service(uow: UowDep, config: SettingsDep) -> CampaignService:
    return CampaignService(uow, media_base_url=config.media_base_url)


def _creative_service(uow: UowDep, config: SettingsDep) -> CreativeService:
    return CreativeService(uow, media_base_url=config.media_base_url)


def _dictionary_service(uow: UowDep) -> DictionaryService:
    return DictionaryService(uow)


def _media_service(
    uow: UowDep, store: MediaStoreDep, storage: StorageDep, config: SettingsDep
) -> MediaService:
    return MediaService(
        uow,
        store,
        storage,
        max_bytes=config.media_upload_max_bytes,
        max_total_bytes=config.media_upload_max_total_bytes,
    )


def _studio_service(
    request: Request, uow: UowDep, store: MediaStoreDep, storage: StorageDep, config: SettingsDep
) -> StudioService:
    return StudioService(
        uow,
        store,
        storage,
        max_bytes=config.media_upload_max_bytes,
        max_total_bytes=config.media_upload_max_total_bytes,
        generator=request.app.state.studio_designer,
    )


AuthServiceDep = Annotated[AuthService, Depends(_auth_service)]
CampaignServiceDep = Annotated[CampaignService, Depends(_campaign_service)]
CreativeServiceDep = Annotated[CreativeService, Depends(_creative_service)]
DictionaryServiceDep = Annotated[DictionaryService, Depends(_dictionary_service)]
MediaServiceDep = Annotated[MediaService, Depends(_media_service)]
StudioServiceDep = Annotated[StudioService, Depends(_studio_service)]
