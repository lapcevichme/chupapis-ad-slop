from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import ANONYMOUS, MANAGER, build_settings, initialize_database
from tests.test_scenario import CAMPAIGN


def test_request_context_headers_and_error_envelope(client):
    headers = {"X-Request-ID": "campaign-check"}
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "campaign-check"
    invalid = client.post("/campaigns", json={}, headers=headers)
    assert invalid.status_code == 400
    assert "errors" in invalid.json()
    assert invalid.headers["X-Request-ID"] == "campaign-check"


def test_unauthenticated_request_gets_401_in_the_common_envelope(client):
    response = client.get("/campaigns", headers=ANONYMOUS)
    assert response.status_code == 401
    assert response.json()["errors"][0]["code"] == "NOT_AUTHENTICATED"


def test_readiness_checks_all_dependencies(client):
    response = client.get("/ready", headers=ANONYMOUS)
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok", "storage": "ok"},
    }


def test_media_url_validation_uses_application_settings():
    app = create_app(build_settings(media_base_url="/custom-media"))
    with TestClient(app) as client:
        client.portal.call(initialize_database, app)
        client.headers.update(MANAGER)
        body = {
            "name": "Настроенный префикс медиа",
            "bannerTypeId": 2,
            "content": {"actionType": "default", "image": {"url": "/custom-media/banner.png"}},
        }
        assert client.post("/campaigns/101/banners", json=body).status_code == 201
        assert client.get("/campaigns/101/warnings").json()["errors"] == []
        body["content"]["image"]["url"] = "/api/media/banner.png"
        assert client.post("/campaigns/101/banners", json=body).status_code == 400


def test_applications_have_independent_settings():
    apps = [create_app(build_settings()), create_app(build_settings(media_base_url="/other"))]
    assert not hasattr(apps[0].state, "db")
    with TestClient(apps[0]) as first:
        first.portal.call(initialize_database, apps[0])
        first.headers.update(MANAGER)
        assert first.post("/campaigns", json=CAMPAIGN).status_code == 201
    assert apps[0].state.settings is not apps[1].state.settings
    assert apps[1].state.settings.media_base_url == "/other"
