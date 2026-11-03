from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuthSession


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, auth_session: AuthSession) -> None:
        self._session.add(auth_session)

    async def get_for_update(self, session_id: UUID) -> AuthSession | None:
        # The lock makes two parallel refreshes with the same token serialize:
        # the second one sees the rotated hash and is treated as reuse.
        stmt = (
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(stmt)

    async def revoke_all(self, user_id: UUID, *, now: datetime) -> int:
        stmt = (
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
            .execution_options(synchronize_session=False)
        )
        result: CursorResult[tuple[()]] = await self._session.execute(stmt)  # type: ignore[assignment]
        return result.rowcount

    async def delete_stale(self, *, before: datetime) -> int:
        stmt = delete(AuthSession).where(
            or_(AuthSession.expires_at < before, AuthSession.revoked_at < before)
        )
        result: CursorResult[tuple[()]] = await self._session.execute(stmt)  # type: ignore[assignment]
        return result.rowcount
