from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import fail
from app.db.models import User
from app.db.uow import UnitOfWork
from app.domain.enums import Role
from app.domain.users import (
    CurrentUser,
    UserProfile,
    UserQuery,
    ensure_can_ban,
    ensure_can_change_role,
)
from app.service.mappers import to_profile


class AdminUserService:
    def __init__(self, uow: UnitOfWork, actor: CurrentUser) -> None:
        self._uow = uow
        self._actor = actor

    async def list_users(self, query: UserQuery) -> list[UserProfile]:
        return [to_profile(user) for user in await self._uow.users.search(query)]

    async def ban(self, user_id: UUID) -> UserProfile:
        user = await self._locked(user_id)
        ensure_can_ban(self._actor, target_id=user.id, target_role=user.role)
        if user.banned_at is None:
            now = datetime.now(UTC)
            user.banned_at = now
            user.auth_version += 1
            await self._uow.sessions.revoke_all(user.id, now=now)
        await self._uow.flush()
        return to_profile(user)

    async def unban(self, user_id: UUID) -> UserProfile:
        user = await self._locked(user_id)
        user.banned_at = None
        await self._uow.flush()
        return to_profile(user)

    async def set_role(self, user_id: UUID, role: Role) -> UserProfile:
        user = await self._locked(user_id)
        ensure_can_change_role(self._actor, target_id=user.id)
        user.role = role
        # Права зависят от роли, поэтому выданные токены перестают действовать.
        user.auth_version += 1
        await self._uow.flush()
        return to_profile(user)

    async def _locked(self, user_id: UUID) -> User:
        user = await self._uow.users.get(user_id, for_update=True)
        if user is None:
            raise fail("USER_NOT_FOUND", status=404)
        return user
