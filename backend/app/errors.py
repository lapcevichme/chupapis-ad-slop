from typing import Any

from pydantic import BaseModel

from app.domain.rules import ERRORS


class ApiError(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    errors: list[ApiError]


def api_error(code: str, field: str | None = None, message: str | None = None) -> ApiError:
    return ApiError(code=code, message=message or ERRORS[code], field=field)


class ApiException(Exception):
    def __init__(self, errors: list[ApiError], status_code: int = 400):
        self.errors = errors
        self.status_code = status_code


def fail(code: str, field: str | None = None, message: str | None = None) -> ApiException:
    return ApiException([api_error(code, field, message)])


def not_found(field: str, value: Any) -> ApiException:
    return ApiException([api_error("ENTITY_NOT_FOUND", field, f"Не найдено: {field}={value}")], status_code=404)


def raise_if(errors: list[ApiError]) -> None:
    if errors:
        raise ApiException(errors)
