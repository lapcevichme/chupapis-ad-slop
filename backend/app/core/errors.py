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
    """Ожидаемая ошибка. `keep_changes` помечает редкую ошибку, после которой транзакцию нужно закоммитить:
    например, повторное использование refresh-токена отзывает сессию и всё равно отвечает 401."""

    def __init__(
        self,
        errors: list[ApiError],
        status_code: int = 400,
        *,
        keep_changes: bool = False,
        headers: list[tuple[str, str]] | None = None,
    ):
        self.errors = errors
        self.status_code = status_code
        self.keep_changes = keep_changes
        self.headers = headers or []
        super().__init__("; ".join(error.message for error in errors))


def fail(
    code: str,
    field: str | None = None,
    message: str | None = None,
    *,
    status: int = 400,
    keep_changes: bool = False,
) -> DomainError:
    return DomainError([api_error(code, field, message)], status, keep_changes=keep_changes)


def unauthorized(
    code: str = "NOT_AUTHENTICATED", message: str | None = None, *, keep_changes: bool = False
) -> DomainError:
    return fail(code, message=message, status=401, keep_changes=keep_changes)


def forbidden(code: str = "ROLE_FORBIDDEN", message: str | None = None) -> DomainError:
    return fail(code, message=message, status=403)


def not_found(field: str, value: Any) -> DomainError:
    return DomainError(
        [api_error("ENTITY_NOT_FOUND", field, f"Не найдено: {field}={value}")], status_code=404
    )


def raise_if(errors: list[ApiError]) -> None:
    if errors:
        raise DomainError(errors)
