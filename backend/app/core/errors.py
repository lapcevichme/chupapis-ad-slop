from dataclasses import dataclass
from typing import Any

from app.core.codes import ERRORS


@dataclass(frozen=True, slots=True)
class ApiError:
    code: str
    message: str
    field: str | None = None


def api_error(code: str, field: str | None = None, message: str | None = None) -> ApiError:
    return ApiError(code=code, message=message or ERRORS[code], field=field)


class DomainError(Exception):
    def __init__(self, errors: list[ApiError], status_code: int = 400):
        self.errors = errors
        self.status_code = status_code
        super().__init__("; ".join(error.message for error in errors))


def fail(code: str, field: str | None = None, message: str | None = None) -> DomainError:
    return DomainError([api_error(code, field, message)])


def not_found(field: str, value: Any) -> DomainError:
    return DomainError(
        [api_error("ENTITY_NOT_FOUND", field, f"Не найдено: {field}={value}")], status_code=404
    )


def raise_if(errors: list[ApiError]) -> None:
    if errors:
        raise DomainError(errors)
