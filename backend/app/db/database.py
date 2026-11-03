from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.errors import DomainError
from app.db.uow import UnitOfWork


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url,
            echo=settings.sql_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncIterator[UnitOfWork]:
        """Коммит при успехе, откат при любой ошибке (кроме той, что просит сохранить изменения)."""
        async with self._sessions() as session:
            try:
                yield UnitOfWork(session)
            except DomainError as exc:
                if exc.keep_changes:
                    await session.commit()
                else:
                    await session.rollback()
                raise
            except BaseException:
                await session.rollback()
                raise
            await session.commit()

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self.engine.dispose()

    def raw_session(self) -> AsyncSession:
        """Для тестов и скриптов, которым нужна обычная сессия вне правил UoW."""
        return self._sessions()
