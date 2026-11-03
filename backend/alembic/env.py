import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import MigrationSettings
from app.db import models  # noqa: F401 - регистрирует таблицы в metadata
from app.db.base import Base

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    # Тесты передают адрес через config.attributes, остальные берут его из настроек.
    return str(config.attributes.get("database_url") or MigrationSettings().database_url)


def include_object(
    object_: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    # Таблицы чекпоинтов LangGraph живут в той же БД, но ими управляет сама библиотека
    # (python -m app.cli setup-checkpointer). Без фильтра autogenerate предложил бы их удалить.
    return not (type_ == "table" and reflected and (name or "").startswith("checkpoint"))


def run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(database_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_online())
