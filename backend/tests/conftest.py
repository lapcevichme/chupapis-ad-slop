import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base
from app.db.seed import seed
from app.main import create_app

MANAGER = {"X-User": "ivanov.p", "X-Role": "campaignManager"}
MODERATOR = {"X-User": "petrova.m", "X-Role": "campaignModerator"}


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        checkpoint_db=tmp_path / "checkpoints.db",
        media_dir=tmp_path / "media",
        llm_api_key="",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        client.portal.call(initialize_database, app)
        yield client


def codes(response) -> list[str]:
    return [e["code"] for e in response.json()["errors"]]


async def initialize_database(app):
    async with app.state.db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with app.state.db.unit_of_work() as uow:
        await uow.session.run_sync(seed, app.state.settings.seed_dir)
