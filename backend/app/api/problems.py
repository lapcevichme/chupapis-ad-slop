from dataclasses import asdict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import DomainError
from app.infra.pydantic_errors import map_pydantic_errors


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"errors": [asdict(error) for error in exc.errors]}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = map_pydantic_errors(exc.errors(), strip=1)
        return JSONResponse(
            status_code=400, content={"errors": [asdict(error) for error in errors]}
        )
