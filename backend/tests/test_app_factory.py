from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db import Base
from app.main import create_app
from app.seed import seed
from tests.conftest import MANAGER
from tests.test_scenario import CAMPAIGN


def test_applications_have_independent_settings_and_databases(tmp_path):
    apps = [
        create_app(Settings(
            _env_file=None,
            database_url=f"sqlite:///{tmp_path / name / 'data.db'}",
            checkpoint_db=tmp_path / name / "checkpoints.db",
            media_dir=tmp_path / name / "media",
            llm_api_key="",
        ))
        for name in ("first", "second")
    ]
    assert not hasattr(apps[0].state, "db")
    with TestClient(apps[0]) as first, TestClient(apps[1]) as second:
        for app in apps:
            Base.metadata.create_all(app.state.db.engine)
            with app.state.db.sessions() as session:
                seed(session)
        created = first.post("/campaigns", headers=MANAGER, json=CAMPAIGN)
        assert created.status_code == 201
        assert second.get(f"/campaigns/{created.json()['id']}").status_code == 404
        assert apps[0].state.settings is not apps[1].state.settings
