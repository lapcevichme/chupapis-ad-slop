from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.domain.pydantic_errors import map_pydantic_errors
from app.errors import ApiException
from app.routers import campaigns, cbro, children, dictionaries


def _operation_id(route: APIRoute) -> str:
    # operationId = имя функции: из него получаются имена TS-клиента и инструментов агента.
    return route.name


app = FastAPI(title="AdPilot AI — API кампаний", version="0.1.0", generate_unique_id_function=_operation_id)

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

settings.media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}
