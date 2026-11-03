from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.middleware import RequestContextMiddleware
from app.api.openapi import ApiApplication
from app.api.problems import register_exception_handlers
from app.api.router import api_router
from app.bootstrap import build_chat_service, build_speech_service, build_studio_designer
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.security.tokens import TokenCodec
from app.db.database import Database
from app.infra.checkpointer import postgres_checkpointer
from app.infra.storage import ObjectStorage
from app.service.chat_sessions import SessionRegistry
from app.service.media import MediaStore


def create_app(settings: Settings | None = None) -> FastAPI:
    """Фабрика: `uvicorn app.main:create_app --factory`. Тесты зовут её со своими настройками,
    при импорте ничего не создаётся."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, as_json=settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db = Database(settings)
        app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        app.state.storage = ObjectStorage.from_settings(settings)
        app.state.media_store = MediaStore(
            app.state.db, app.state.storage, media_base_url=settings.media_base_url
        )
        try:
            if settings.storage_auto_create_bucket:
                await app.state.storage.ensure_bucket()
            async with postgres_checkpointer(settings) as saver:
                app.state.checkpointer = saver
                app.state.chat = build_chat_service(
                    saver,
                    settings,
                    SessionRegistry(app.state.db),
                    media=app.state.media_store,
                )
                app.state.speech = build_speech_service(settings)
                app.state.studio_designer = build_studio_designer(settings)
                yield
        finally:
            await app.state.redis.aclose()
            await app.state.db.dispose()

    docs = settings.show_api_docs
    app = ApiApplication(
        title="AdPilot AI — API кампаний",
        version="0.2.0",
        generate_unique_id_function=lambda route: route.name,
        lifespan=lifespan,
        debug=settings.debug,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.settings = settings
    app.state.token_codec = TokenCodec.from_settings(settings)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )
    # Добавлено последним = снаружи: id запроса получает любой ответ, включая preflight и ошибки.
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app
