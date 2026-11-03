from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.infra.llm import NoImageGenerator
from app.main import create_app
from tests.conftest import MANAGER, build_settings, initialize_database, install_chat
from tests.test_agent import ScriptedModel, call, events, tool_message
from tests.test_scenario import CAMPAIGN


def install(client, script):
    install_chat(
        client.app,
        chat=ScriptedModel(script=script),
        design=ScriptedModel(script=[]),
        images=NoImageGenerator(),
    )


def test_pending_confirmation_survives_application_restart():
    settings = build_settings()
    with TestClient(create_app(settings)) as client:
        client.headers.update(MANAGER)
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
        client.headers.update(MANAGER)
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
