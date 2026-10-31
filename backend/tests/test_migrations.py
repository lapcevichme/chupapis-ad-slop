from pathlib import Path

from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command
from app.core.config import Settings
from app.db.seed import seed
from app.main import create_app


def test_existing_revisions_upgrade_and_match_models(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "7dc609e004b8")
    command.upgrade(config, "head")
    command.check(config)
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        checkpoint_db=tmp_path / "checkpoints.db",
        media_dir=tmp_path / "media",
        llm_api_key="",
    )
    app = create_app(settings)
    with TestClient(app) as client:

        async def load_seed():
            async with app.state.db.unit_of_work() as uow:
                return await uow.session.run_sync(seed, settings.seed_dir)

        assert client.portal.call(load_seed) is True
        assert client.portal.call(load_seed) is False
        assert client.get("/campaigns/101").json()["name"] == "Премиальная карта: осенняя акция"
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.check(config)
