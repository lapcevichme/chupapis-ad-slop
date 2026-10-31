from dataclasses import dataclass
from typing import Annotated

from fastapi import Header

from app.domain.enums import Role
from app.errors import fail


@dataclass(frozen=True)
class Actor:
    login: str
    role: Role | None


def get_actor(
    x_user: Annotated[str | None, Header(alias="X-User")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
) -> Actor:
    """Пользователь пишущего запроса. Неизвестная роль равносильна отсутствию прав: проверка роли вернёт ROLE_FORBIDDEN."""
    if not x_user:
        raise fail("USER_REQUIRED")
    role = Role(x_role) if x_role in set(Role) else None
    return Actor(login=x_user, role=role)


def require_role(actor: Actor, role: Role) -> None:
    if actor.role != role:
        raise fail("ROLE_FORBIDDEN", message=f"Действие доступно только роли {role}")
