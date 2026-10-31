from dataclasses import dataclass

from app.core.errors import fail
from app.domain.enums import Role


@dataclass(frozen=True, slots=True)
class Actor:
    login: str
    role: Role | None


def require_role(actor: Actor, role: Role) -> None:
    if actor.role != role:
        raise fail("ROLE_FORBIDDEN", message=f"Действие доступно только роли {role}")
