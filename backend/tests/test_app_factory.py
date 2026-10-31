from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import MANAGER, initialize_database
from tests.test_scenario import CAMPAIGN


def test_request_context_headers_and_error_envelope(client):
    headers = MANAGER | {"X-Request-ID": "campaign-check"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "campaign-check"
    assert response.headers["X-User"] == MANAGER["X-User"]
    assert response.headers["X-Role"] == MANAGER["X-Role"]
    invalid = client.post("/campaigns", json={}, headers=headers)
    assert invalid.status_code == 400
    assert "errors" in invalid.json()
    assert invalid.headers["X-Request-ID"] == "campaign-check"


def test_applications_have_independent_settings_and_databases(tmp_path):
    apps = [
        create_app(
            Settings(
                _env_file=None,
                database_url=f"sqlite:///{tmp_path / name / 'data.db'}",
                checkpoint_db=tmp_path / name / "checkpoints.db",
                media_dir=tmp_path / name / "media",
                llm_api_key="",
            )
        )
        for name in ("first", "second")
    ]
    assert not hasattr(apps[0].state, "db")
    with TestClient(apps[0]) as first, TestClient(apps[1]) as second:
        first.portal.call(initialize_database, apps[0])
        second.portal.call(initialize_database, apps[1])
        created = first.post("/campaigns", headers=MANAGER, json=CAMPAIGN)
        assert created.status_code == 201
        assert second.get(f"/campaigns/{created.json()['id']}").status_code == 404
        assert apps[0].state.settings is not apps[1].state.settings
