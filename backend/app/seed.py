import asyncio

from app.core.config import get_settings
from app.db.database import Database
from app.db.seed import seed


async def main() -> None:
    settings = get_settings()
    database = Database(settings)
    password = settings.demo_users_password
    try:
        async with database.unit_of_work() as uow:
            changed = await seed(
                uow.session,
                settings.seed_dir,
                demo_password=password.get_secret_value() if password else None,
            )
        print("Данные загружены" if changed else "БД уже заполнена, сид пропущен")
    finally:
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
