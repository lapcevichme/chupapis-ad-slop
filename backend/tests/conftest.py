import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db import Base
from app.main import create_app
from app.seed import seed

MANAGER = {"X-User": "ivanov.p", "X-Role": "campaignManager"}
MODERATOR = {"X-User": "petrova.m", "X-Role": "campaignModerator"}


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        checkpoint_db=tmp_path / 'checkpoints.db',
        media_dir=tmp_path / 'media',
        llm_api_key="",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        Base.metadata.create_all(app.state.db.engine)
        with app.state.db.sessions() as session:
            seed(session)
        yield client


def codes(response) -> list[str]:
    return [e["code"] for e in response.json()["errors"]]
