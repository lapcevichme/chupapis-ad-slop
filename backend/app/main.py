from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.router import api_router
from app.bootstrap import build_chat_service
from app.contracts.chat import EVENT_MODELS
from app.core.config import Settings
from app.core.errors import DomainError
from app.db.database import Database
from app.infra.pydantic_errors import map_pydantic_errors
from app.service.chat_sessions import SessionRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db = Database(settings)
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        settings.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_db)) as saver:
                app.state.checkpointer = saver
                app.state.chat = build_chat_service(saver, settings, SessionRegistry(app.state.db))
                yield
        finally:
            await app.state.db.dispose()

    app = FastAPI(
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
    )

    @app.middleware("http")
    async def echo_user_headers(request: Request, call_next):
        response = await call_next(request)
        for header in ("X-User", "X-Role"):
            if value := request.headers.get(header):
                response.headers[header] = value
        return response

    @app.exception_handler(DomainError)
    async def handle_api_exception(_request: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code, content={"errors": [asdict(e) for e in exc.errors]}
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError):
        errors = map_pydantic_errors(exc.errors(), strip=1)
        return JSONResponse(status_code=400, content={"errors": [asdict(e) for e in errors]})

    app.include_router(api_router)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for model in EVENT_MODELS.values():
            model_schema = model.model_json_schema(
                ref_template="#/components/schemas/{model}", mode="serialization"
            )
            components.update(model_schema.pop("$defs", {}))
            components[model.__name__] = model_schema
        schema["x-chat-events"] = {
            event: f"#/components/schemas/{model.__name__}" for event, model in EVENT_MODELS.items()
        }
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
    app.mount("/media", StaticFiles(directory=settings.media_dir, check_dir=False), name="media")

    @app.get("/health", tags=["service"])
    def health():
        return {"status": "ok"}

    return app
