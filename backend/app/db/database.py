from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.db.uow import UnitOfWork


def async_url(url: str) -> str:
    parsed = make_url(url)
    if parsed.drivername == "sqlite":
        parsed = parsed.set(drivername="sqlite+aiosqlite")
    return parsed.render_as_string(hide_password=False)


class Database:
    def __init__(self, settings: Settings) -> None:
        url = make_url(async_url(settings.database_url))
        if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_async_engine(url, pool_pre_ping=True)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        if url.get_backend_name() == "sqlite":

            @event.listens_for(self.engine.sync_engine, "connect")
            def enable_foreign_keys(connection: Any, _record: Any) -> None:
                connection.execute("PRAGMA foreign_keys=ON")

    @asynccontextmanager
    async def unit_of_work(self) -> AsyncIterator[UnitOfWork]:
        async with self.sessions() as session:
            try:
                yield UnitOfWork(session)
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        await self.engine.dispose()
