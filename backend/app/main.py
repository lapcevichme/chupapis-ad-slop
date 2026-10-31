from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.middleware import RequestContextMiddleware
from app.api.openapi import ApiApplication
from app.api.problems import register_exception_handlers
from app.api.router import api_router
from app.bootstrap import build_chat_service
from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.database import Database
from app.service.chat_sessions import SessionRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level, as_json=settings.log_json)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db = Database(settings)
        try:
            settings.media_dir.mkdir(parents=True, exist_ok=True)
            settings.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
            async with AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_db)) as saver:
                app.state.checkpointer = saver
                app.state.chat = build_chat_service(saver, settings, SessionRegistry(app.state.db))
                yield
        finally:
            await app.state.db.dispose()

    app = ApiApplication(
        title="AdPilot AI — API кампаний",
        version="0.1.0",
        generate_unique_id_function=lambda route: route.name,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-User", "X-Role"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)
    app.mount("/media", StaticFiles(directory=settings.media_dir, check_dir=False), name="media")
    return app
