import asyncio

from app.core.config import Settings
from app.db.database import Database
from app.db.seed import seed


async def main() -> None:
    settings = Settings()
    database = Database(settings)
    try:
        async with database.unit_of_work() as uow:
            changed = await uow.session.run_sync(seed, settings.seed_dir)
        print("Моки загружены" if changed else "БД уже заполнена, сид пропущен")
    finally:
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
