import asyncio
from logging.config import fileConfig

from alembic import context
from app.core.config import Settings
from app.db import models
from app.db.database import Database, async_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def migrate(connection) -> None:
    context.configure(
        connection=connection, target_metadata=models.Campaign.metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def online() -> None:
    database = Database(Settings())
    try:
        async with database.engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await database.dispose()


if context.is_offline_mode():
    context.configure(
        url=async_url(Settings().database_url),
        target_metadata=models.Campaign.metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
