from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.core.errors import fail, forbidden
from app.domain.enums import Role


class Permission(StrEnum):
    CAMPAIGNS_READ = "campaigns:read"
    CAMPAIGNS_WRITE = "campaigns:write"
    CAMPAIGNS_MODERATE = "campaigns:moderate"
    DICTIONARIES_WRITE = "dictionaries:write"
    MEDIA_WRITE = "media:write"
    USERS_READ = "users:read"
    USERS_BAN = "users:ban"
    USERS_MANAGE_ROLES = "users:manage_roles"
    STATS_READ = "stats:read"


_READ = frozenset({Permission.CAMPAIGNS_READ})

# Роли — это код, а не данные: роль это именованный набор прав, и проверка не ходит в БД.
# Одобрять и возвращать кампании может только модератор, даже админ: это решение человека-модератора.
ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    Role.MANAGER: _READ
    | {Permission.CAMPAIGNS_WRITE, Permission.DICTIONARIES_WRITE, Permission.MEDIA_WRITE},
    Role.MODERATOR: _READ | {Permission.CAMPAIGNS_MODERATE},
    Role.ADMIN: _READ
    | {
        Permission.USERS_READ,
        Permission.USERS_BAN,
        Permission.USERS_MANAGE_ROLES,
        Permission.STATS_READ,
    },
}


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Кто вызывает. Единственный объект пользователя, который видит API-слой."""

    id: UUID
    username: str
    role: Role
    session_id: UUID

    def can(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]


@dataclass(frozen=True, slots=True)
class UserProfile:
    id: UUID
    email: str
    username: str
    role: Role
    is_banned: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UserQuery:
    search: str | None = None
    role: Role | None = None
    banned: bool | None = None
    limit: int = 50
    offset: int = 0


def normalize_email(email: str) -> str:
    return email.strip().lower()


def ensure_can(user: CurrentUser, permission: Permission) -> None:
    if not user.can(permission):
        raise forbidden(message=f"Действие недоступно для роли {user.role}")


def ensure_can_ban(actor: CurrentUser, *, target_id: UUID, target_role: Role) -> None:
    if actor.id == target_id:
        raise fail("SELF_MODERATION", status=403)
    if target_role is Role.ADMIN:
        raise fail("ADMIN_PROTECTED", status=403)


def ensure_can_change_role(actor: CurrentUser, *, target_id: UUID) -> None:
    # Последний админ не должен запереть всех, разжаловав себя.
    if actor.id == target_id:
        raise fail("SELF_MODERATION", status=403)
