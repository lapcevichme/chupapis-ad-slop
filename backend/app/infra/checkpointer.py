from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings


def _pool(settings: Settings, *, max_size: int) -> AsyncConnectionPool:
    # Настройки соединения те же, что внутри AsyncPostgresSaver.from_conn_string.
    return AsyncConnectionPool(
        settings.psycopg_url,
        min_size=1,
        max_size=max_size,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )


@asynccontextmanager
async def postgres_checkpointer(settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
    """Состояние диалогов агента живёт в той же Postgres, что и остальные данные."""
    pool = _pool(settings, max_size=settings.db_pool_size)
    await pool.open()
    try:
        yield AsyncPostgresSaver(pool)  # type: ignore[arg-type]
    finally:
        await pool.close()


async def setup_checkpointer(settings: Settings) -> None:
    """Создаёт таблицы чекпоинтов. Запускается шагом миграции, а не при каждом старте API."""
    async with postgres_checkpointer(settings) as saver:
        await saver.setup()
