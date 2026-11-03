from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.domain.users import UserQuery


def _like_pattern(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, user: User) -> None:
        self._session.add(user)

    async def get(self, user_id: UUID, *, for_update: bool = False) -> User | None:
        if not for_update:
            return await self._session.get(User, user_id)
        # Блокировка строки для «прочитал-изменил» (бан, смена роли, рост auth_version).
        stmt = (
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(stmt)

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))

    async def get_by_username(self, username: str) -> User | None:
        return await self._session.scalar(
            select(User).where(func.lower(User.username) == username.lower())
        )

    async def search(self, query: UserQuery) -> Sequence[User]:
        stmt = select(User)
        if query.search:
            pattern = _like_pattern(query.search.strip())
            stmt = stmt.where(
                or_(
                    User.email.ilike(pattern, escape="\\"),
                    User.username.ilike(pattern, escape="\\"),
                )
            )
        if query.role is not None:
            stmt = stmt.where(User.role == query.role)
        if query.banned is not None:
            stmt = stmt.where(
                User.banned_at.is_not(None) if query.banned else User.banned_at.is_(None)
            )
        stmt = stmt.order_by(User.created_at.desc(), User.id.desc())
        return (await self._session.scalars(stmt.limit(query.limit).offset(query.offset))).all()
