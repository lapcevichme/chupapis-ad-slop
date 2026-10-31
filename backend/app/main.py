from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from app.agent.events import EVENT_MODELS
from app.agent.factory import build_chat_service
from app.config import settings
from app.domain.pydantic_errors import map_pydantic_errors
from app.errors import ApiException
from app.routers import campaigns, cbro, chat, children, dictionaries


def _operation_id(route: APIRoute) -> str:
    # operationId = имя функции: из него получаются имена TS-клиента и инструментов агента.
    return route.name


@asynccontextmanager
async def lifespan(app: FastAPI):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
    # Состояние диалогов и черновиков переживает перезапуск: checkpointer LangGraph в SQLite.
    async with AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_db)) as checkpointer:
        app.state.chat = build_chat_service(checkpointer)
        yield


app = FastAPI(title="AdPilot AI — API кампаний", version="0.1.0", generate_unique_id_function=_operation_id, lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def echo_user_headers(request: Request, call_next):
    """§3: бэкенд возвращает X-User и X-Role в ответе."""
    response = await call_next(request)
    for header in ("X-User", "X-Role"):
        if value := request.headers.get(header):
            response.headers[header] = value
    return response


@app.exception_handler(ApiException)
async def handle_api_exception(_request: Request, exc: ApiException):
    return JSONResponse(status_code=exc.status_code, content={"errors": [e.model_dump() for e in exc.errors]})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, exc: RequestValidationError):
    # loc начинается с источника (body, path, query, header), его отрезаем.
    errors = map_pydantic_errors(exc.errors(), strip=1)
    return JSONResponse(status_code=400, content={"errors": [e.model_dump() for e in errors]})


app.include_router(dictionaries.router)
app.include_router(campaigns.router)
app.include_router(children.router)
app.include_router(cbro.router)
app.include_router(chat.router)


def custom_openapi():
    """Добавляет схемы событий SSE (ChatEvent*), которых FastAPI сам не видит (chat-api.md §1)."""
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    for model in EVENT_MODELS.values():
        model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}", mode="serialization")
        components.update(model_schema.pop("$defs", {}))
        components[model.__name__] = model_schema
    schema["x-chat-events"] = {event: f"#/components/schemas/{model.__name__}" for event, model in EVENT_MODELS.items()}
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

settings.media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}
