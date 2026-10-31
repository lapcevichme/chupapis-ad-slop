import httpx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.bootstrap import build_chat_service
from app.core.config import Settings
from app.infra.campaigns_api import CampaignsApi
from app.infra.llm import NoImageGenerator
from app.main import create_app
from app.service.chat_sessions import SessionRegistry
from tests.conftest import MANAGER, initialize_database
from tests.test_agent import ScriptedModel, call, events, tool_message
from tests.test_scenario import CAMPAIGN


def install(client, script):
    app = client.app
    app.state.chat = build_chat_service(
        app.state.checkpointer,
        app.state.settings,
        SessionRegistry(app.state.db),
        chat=ScriptedModel(script=script),
        design=ScriptedModel(script=[]),
        images=NoImageGenerator(),
        api_factory=lambda user, role: CampaignsApi(
            user, role, base_url="http://api", transport=httpx.ASGITransport(app=app)
        ),
    )


def test_pending_confirmation_survives_application_restart(tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'data.db'}",
        checkpoint_db=tmp_path / "checkpoints.db",
        media_dir=tmp_path / "media",
        llm_api_key="",
    )
    with TestClient(create_app(settings)) as client:
        client.portal.call(initialize_database, client.app)
        install(
            client,
            [
                tool_message(
                    call("propose_create_campaign", {"campaign": CAMPAIGN}, 1),
                    call("request_confirmation", {"title": "Создать кампанию"}, 2),
                )
            ],
        )
        sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]
        response = client.post(f"/chat/{sid}/messages", json={"text": "Создай"}, headers=MANAGER)
        confirmation = next(
            data for kind, data in events(response) if kind == "confirmation_required"
        )
        assert all(row["name"] != CAMPAIGN["name"] for row in client.get("/campaigns").json())

    with TestClient(create_app(settings)) as client:
        install(client, [AIMessage(content="Кампания сохранена")])
        snapshot = client.get(f"/chat/{sid}", headers=MANAGER).json()
        assert snapshot["messages"][0]["text"] == "Создай"
        assert snapshot["pendingConfirmation"]["id"] == confirmation["id"]
        path = f"/chat/{sid}/confirmations/{confirmation['id']}"
        result = events(client.post(path, json={"approved": True}, headers=MANAGER))
        assert "campaign_updated" in [kind for kind, _ in result]
        client.post(path, json={"approved": True}, headers=MANAGER)
        saved = [row for row in client.get("/campaigns").json() if row["name"] == CAMPAIGN["name"]]
        assert len(saved) == 1
        audit = client.get(f"/campaigns/{saved[0]['id']}/audit").json()
        assert len(audit) == 1 and audit[0]["action"] == "CREATE"
