from sqlalchemy import create_engine, inspect

from alembic import command
from tests.conftest import TEST_DATABASE_URL, alembic_config


def test_models_match_migrations():
    """Поменял модель и забыл миграцию: тест упадёт (autogenerate видит расхождение)."""
    command.check(alembic_config())


def test_downgrade_and_upgrade_again():
    config = alembic_config()
    command.downgrade(config, "base")
    engine = create_engine(TEST_DATABASE_URL.replace("+asyncpg", "+psycopg"))
    try:
        tables = set(inspect(engine).get_table_names())
        assert "campaigns" not in tables and "users" not in tables
    finally:
        engine.dispose()
    command.upgrade(config, "head")
