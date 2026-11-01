from langchain_core.messages import AIMessage

from tests.conftest import MANAGER, MODERATOR
from tests.test_persistence import install


def test_chat_trash_preserves_history_campaign_and_owner(client):
    install(client, [AIMessage(content="Помогу с креативом")])
    sid = client.post("/chat", json={"campaignId": 103}, headers=MANAGER).json()["sessionId"]
    client.post(f"/chat/{sid}/messages", json={"text": "Привет"}, headers=MANAGER)
    assert client.get(f"/chat/{sid}", headers=MODERATOR).status_code == 404
    assert client.delete(f"/chat/{sid}", headers=MODERATOR).status_code == 404
    assert client.delete(f"/chat/{sid}", headers=MANAGER).status_code == 200
    assert client.delete(f"/chat/{sid}", headers=MANAGER).status_code == 200
    assert client.get("/chat", headers=MANAGER).json() == []
    trash = client.get("/chat?archived=true", headers=MANAGER).json()
    assert trash[0]["campaignId"] == 103 and trash[0]["archivedAt"]
    assert client.get("/chat?archived=true", headers=MODERATOR).json() == []
    assert client.get(f"/chat/{sid}", headers=MANAGER).status_code == 404
    assert (
        client.post(f"/chat/{sid}/messages", json={"text": "Правка"}, headers=MANAGER).status_code
        == 404
    )
    assert client.get("/campaigns/103").status_code == 200
    assert client.post(f"/chat/{sid}/restore", headers=MODERATOR).status_code == 404
    assert client.post(f"/chat/{sid}/restore", headers=MANAGER).status_code == 200
    history = client.get(f"/chat/{sid}", headers=MANAGER).json()["messages"]
    assert history[0]["text"] == "Привет"
    assert history[-1]["text"] == "Помогу с креативом"
    assert (
        client.post("/chat", json={"campaignId": 103}, headers=MANAGER).json()["sessionId"] == sid
    )


def test_restore_conflict_keeps_both_chats(client):
    install(client, [])
    first = client.post("/chat", json={"campaignId": 103}, headers=MANAGER).json()["sessionId"]
    client.delete(f"/chat/{first}", headers=MANAGER)
    second = client.post("/chat", json={"campaignId": 103}, headers=MANAGER).json()["sessionId"]
    assert first != second
    assert client.post(f"/chat/{first}/restore", headers=MANAGER).status_code == 409
    assert len(client.get("/chat?archived=true", headers=MANAGER).json()) == 1
    client.delete(f"/chat/{second}", headers=MANAGER)
    assert client.post(f"/chat/{first}/restore", headers=MANAGER).status_code == 200


def test_unbound_chat_title_and_busy_protection(client):
    install(client, [AIMessage(content="Привет")])
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]
    client.post(f"/chat/{sid}/messages", json={"text": "Кэшбэк в кафе"}, headers=MANAGER)
    assert client.get("/chat", headers=MANAGER).json()[0]["name"] == "Кэшбэк в кафе"
    client.app.state.chat.active.add(sid)
    assert client.delete(f"/chat/{sid}", headers=MANAGER).status_code == 409
    client.app.state.chat.active.clear()
    assert client.delete(f"/chat/{sid}", headers=MANAGER).status_code == 200
