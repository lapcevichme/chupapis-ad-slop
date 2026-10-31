"""Граф агента на подставных моделях: подтверждение обязательно, записи идут в API только после «да»."""

import json
from typing import Any

import httpx
import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import Field

from app.agent.api_client import CampaignsApi
from app.agent.factory import build_chat_service
from app.agent.llm import NoImageGenerator
from app.main import app
from tests.conftest import MANAGER, MODERATOR
from tests.test_scenario import CAMPAIGN


class ScriptedModel(BaseChatModel):
    """Отдаёт заранее заготовленные ответы по очереди и запоминает, что получила."""

    script: list[AIMessage]
    seen: list[list[Any]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=self.script.pop(0))])


def call(name: str, args: dict[str, Any], i: int) -> dict[str, Any]:
    return {"name": name, "args": args, "id": f"call-{name}-{i}", "type": "tool_call"}


def tool_message(*calls) -> AIMessage:
    return AIMessage(content="", tool_calls=list(calls))


BANNER_OK = {
    "title": "Вклад под 16% годовых",
    "text": "Откройте онлайн за 2 минуты",
    "titleStyle": {"fontSize": 28, "fontWeight": "bold", "textColor": "#FFFFFFFF"},
    "background": {"color": "#21A038FF"},
    "actionType": "default",
}
PROMO_OK = {
    "role": "promo",
    "component": {
        "role": "linearContainer",
        "axis": "v",
        "components": [
            {"role": "text", "format": "html", "text": "<b>16% годовых</b>"},
            {"role": "button", "text": "Открыть вклад", "actionType": "default"},
        ],
    },
}


def design_reply(banner: dict, i: int) -> AIMessage:
    args = {"bannerName": "Сторис: вклад 16%", "banner": banner, "contentName": "Промо: вклад", "content": PROMO_OK}
    return tool_message(call("DesignResult", args, i))


def events(response) -> list[tuple[str, dict]]:
    result = []
    for block in response.text.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line and not line.startswith(":"))
        if "event" in lines:
            result.append((lines["event"], json.loads(lines["data"])))
    return result


@pytest.fixture
def chat(client):
    def api_factory(user, role):
        return CampaignsApi(user, role, base_url="http://api", transport=httpx.ASGITransport(app=app))

    def install(chat_script: list[AIMessage], design_script: list[AIMessage] | None = None, images=None):
        model = ScriptedModel(script=chat_script)
        app.state.chat = build_chat_service(
            InMemorySaver(),
            chat=model,
            design=ScriptedModel(script=design_script or []),
            images=images or NoImageGenerator(),
            api_factory=api_factory,
        )
        return model

    return install


def test_brief_to_moderation_with_confirmation(client, chat):
    campaign = CAMPAIGN | {"tags": []}
    chat(
        [
            tool_message(
                call("propose_create_campaign", {"campaign": campaign}, 1),
                call("propose_set_segments", {"included": ["AGE_26_45", "CITY_MSK"], "excluded": ["EXC_UNSUBSCRIBED"]}, 2),
                call("design_creative", {"brief": "Вклад 16% до конца года", "placeId": 1}, 3),
                call("request_confirmation", {"title": "Создать кампанию"}, 4),
            ),
            AIMessage(content="Кампания создана."),
            tool_message(call("propose_to_moderation", {}, 5), call("request_confirmation", {"title": "На модерацию"}, 6)),
            AIMessage(content="Отправлено на модерацию."),
        ],
        # Первая версия баннера длиннее лимита STORY: дизайн-агент должен исправиться сам.
        [design_reply(BANNER_OK | {"title": "А" * 150}, 1), design_reply(BANNER_OK, 2)],
    )
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]

    first = events(client.post(f"/chat/{sid}/messages", json={"text": "Вклад 16% для 26–45 в Москве"}, headers=MANAGER))
    kinds = [kind for kind, _ in first]
    assert "draft_updated" in kinds and "confirmation_required" in kinds and kinds[-1] == "done"
    draft = next(data for kind, data in first if kind == "draft_updated")
    assert draft["draft"]["banners"][0]["content"]["title"] == "Вклад под 16% годовых"
    assert [c["channelCode"] for c in draft["draft"]["creatives"]] == ["iOS", "ANDROID"]
    assert draft["validation"]["warnings"] == ["У кампании отсутствуют теги"]
    confirmation = next(data for kind, data in first if kind == "confirmation_required")
    assert len(confirmation["operations"]) == 6
    assert confirmation["operations"][1]["label"] == "Сегменты: включить Возраст 26–45, Москва; исключить Исключение. Отписались от рекламы"

    # До подтверждения в API ничего нет.
    names = [c["name"] for c in client.get("/campaigns").json()]
    assert CAMPAIGN["name"] not in names
    snapshot = client.get(f"/chat/{sid}", headers=MANAGER).json()
    assert snapshot["pendingConfirmation"]["id"] == confirmation["id"] and snapshot["campaignId"] is None

    second = events(client.post(f"/chat/{sid}/confirmations/{confirmation['id']}", json={"approved": True}, headers=MANAGER))
    campaign_id = next(data for kind, data in second if kind == "campaign_updated")["campaignId"]
    details = client.get(f"/campaigns/{campaign_id}").json()
    assert (details["state"], len(details["banners"]), len(details["contents"]), len(details["creatives"])) == ("DRAFT", 1, 1, 2)
    assert details["segments"]["included"] == ["AGE_26_45", "CITY_MSK"]

    third = events(client.post(f"/chat/{sid}/messages", json={"text": "Отправь на модерацию"}, headers=MANAGER))
    conf = next(data for kind, data in third if kind == "confirmation_required")
    client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER)
    assert client.get(f"/campaigns/{campaign_id}").json()["state"] == "ON_MODERATION"

    # Повторный ответ на выполненное подтверждение ничего не пишет второй раз.
    client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER)
    actions = [e["action"] for e in client.get(f"/campaigns/{campaign_id}/audit").json()]
    assert actions.count("TO_MODERATION") == 1

    snapshot = client.get(f"/chat/{sid}", headers=MANAGER).json()
    assert snapshot["campaignId"] == campaign_id and snapshot["pendingConfirmation"] is None
    assert [m["role"] for m in snapshot["messages"]] == ["user", "assistant", "user", "assistant"]


def test_message_instead_of_confirmation_rejects(client, chat):
    chat(
        [
            tool_message(call("propose_approve", {"campaignId": 103}, 1), call("request_confirmation", {"title": "Одобрить 103"}, 2)),
            AIMessage(content="Хорошо, не одобряю."),
        ]
    )
    sid = client.post("/chat", json={"campaignId": 103}, headers=MODERATOR).json()["sessionId"]
    client.post(f"/chat/{sid}/messages", json={"text": "Одобри"}, headers=MODERATOR)
    reply = events(client.post(f"/chat/{sid}/messages", json={"text": "Стоп, сначала посмотрю"}, headers=MODERATOR))
    assert ("message_delta", {"text": "Хорошо, не одобряю."}) in reply
    assert client.get("/campaigns/103").json()["state"] == "ON_MODERATION"


def test_api_error_is_reported_to_model(client, chat):
    model_script = [
        tool_message(call("propose_activate", {"campaignId": 101}, 1), call("request_confirmation", {"title": "Активировать"}, 2)),
        AIMessage(content="Активировать нельзя: кампания не одобрена."),
    ]
    model = chat(model_script)
    sid = client.post("/chat", json={"campaignId": 101}, headers=MANAGER).json()["sessionId"]
    conf = next(d for k, d in events(client.post(f"/chat/{sid}/messages", json={"text": "Запусти"}, headers=MANAGER)) if k == "confirmation_required")
    client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER)
    tool_result = next(m for m in reversed(model.seen[-1]) if isinstance(m, ToolMessage)).content
    assert "ACTIVATE_NOT_ALLOWED" in tool_result


def test_invalid_banner_rejected_before_api(client, chat):
    banner = {"name": "Битый", "bannerTypeId": 1, "content": {"actionType": "externalLink", "title": "А" * 120}}
    model = chat([tool_message(call("propose_create_banner", {"campaignId": 101, "banner": banner}, 1)), AIMessage(content="Исправлю.")])
    sid = client.post("/chat", json={"campaignId": 101}, headers=MANAGER).json()["sessionId"]
    client.post(f"/chat/{sid}/messages", json={"text": "Добавь баннер"}, headers=MANAGER)
    tool_result = next(m for m in reversed(model.seen[-1]) if isinstance(m, ToolMessage)).content
    assert "BANNER_TITLE_TOO_LONG" in tool_result and "LINK_REQUIRED" in tool_result
    assert client.get(f"/chat/{sid}", headers=MANAGER).json()["pendingConfirmation"] is None


def test_suggestions_keep_groups(client, chat):
    items = [{"label": "5 ноября", "value": "С 5 ноября", "group": "Дата начала"}, {"label": "Главный экран", "value": "На главном", "group": "Место показа"}]
    chat([tool_message(call("suggest_options", {"items": items}, 1)), AIMessage(content="Что выбираем?")])
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]

    reply = events(client.post(f"/chat/{sid}/messages", json={"text": "Бриф"}, headers=MANAGER))

    suggestions = next(data for kind, data in reply if kind == "suggestions")
    assert suggestions["items"] == items


def test_model_failure_is_human_readable(client, chat):
    import openai
    import httpx as _httpx

    class Failing(ScriptedModel):
        def _generate(self, *args, **kwargs):
            request = _httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            raise openai.InternalServerError("Error code: 500 - upstream", response=_httpx.Response(500, request=request), body=None)

    app.state.chat = build_chat_service(InMemorySaver(), chat=Failing(script=[]), design=ScriptedModel(script=[]), images=NoImageGenerator(),
                                        api_factory=lambda u, r: CampaignsApi(u, r, base_url="http://api", transport=httpx.ASGITransport(app=app)))
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]
    error = next(data for kind, data in events(client.post(f"/chat/{sid}/messages", json={"text": "Привет"}, headers=MANAGER)) if kind == "error")
    assert error["code"] == "LLM_UNAVAILABLE"
    assert "500" not in error["message"] and "Повторить" in error["message"]


def test_one_session_per_campaign_and_user(client, chat):
    chat([])
    manager = client.post("/chat", json={"campaignId": 103}, headers=MANAGER).json()["sessionId"]
    assert client.post("/chat", json={"campaignId": 103}, headers=MANAGER).json()["sessionId"] == manager
    moderator = client.post("/chat", json={"campaignId": 103}, headers=MODERATOR).json()["sessionId"]
    assert moderator != manager
    # Диалог без кампании каждый раз новый.
    assert client.post("/chat", json={}, headers=MANAGER).json()["sessionId"] != client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]


def test_new_campaign_session_is_bound_after_save(client, chat):
    chat(
        [
            tool_message(call("propose_create_campaign", {"campaign": CAMPAIGN}, 1), call("request_confirmation", {"title": "Создать"}, 2)),
            AIMessage(content="Создано."),
        ]
    )
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]
    conf = next(d for k, d in events(client.post(f"/chat/{sid}/messages", json={"text": "Создай"}, headers=MANAGER)) if k == "confirmation_required")
    second = events(client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER))
    campaign_id = next(d for k, d in second if k == "campaign_updated")["campaignId"]
    assert client.post("/chat", json={"campaignId": campaign_id}, headers=MANAGER).json()["sessionId"] == sid


def test_manager_sees_moderator_decision_from_other_chat(client, chat):
    model = chat([AIMessage(content="Кампания на модерации."), AIMessage(content="Её вернули на правки.")])
    sid = client.post("/chat", json={"campaignId": 103}, headers=MANAGER).json()["sessionId"]
    client.post(f"/chat/{sid}/messages", json={"text": "Что с кампанией?"}, headers=MANAGER)
    assert "состояние ON_MODERATION" in model.seen[-1][0].content

    client.post("/campaigns/103/decline", json={"comment": "Добавьте теги"}, headers=MODERATOR)
    client.post(f"/chat/{sid}/messages", json={"text": "А сейчас?"}, headers=MANAGER)
    assert "состояние NEEDS_WORK" in model.seen[-1][0].content
    # Напоминание стоит последним: системный промпт модель перебивает прошлыми сообщениями диалога.
    reminder = model.seen[-1][-1].content
    assert "сейчас в состоянии NEEDS_WORK, с прошлого хода было ON_MODERATION" in reminder


def test_unconfirmed_changes_get_confirmation_card(client, chat):
    # Модель положила правку в пакет и закончила ход без request_confirmation: карточку показывает граф.
    model = chat(
        [
            tool_message(call("propose_create_tag", {"tag": {"name": "Осень"}}, 1)),
            AIMessage(content="Добавил тег."),
            AIMessage(content="Тег создан."),
        ]
    )
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]
    reply = events(client.post(f"/chat/{sid}/messages", json={"text": "Создай тег Осень"}, headers=MANAGER))
    conf = next(data for kind, data in reply if kind == "confirmation_required")
    assert [op["kind"] for op in conf["operations"]] == ["create_tag"]
    assert [data["text"] for kind, data in reply if kind == "message_delta"] == ["Добавил тег."]
    assert "Осень" not in [t["name"] for t in client.get("/tags").json()]

    client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER)
    assert "Осень" in [t["name"] for t in client.get("/tags").json()]
    assert "Пользователь подтвердил" in next(m for m in reversed(model.seen[-1]) if isinstance(m, ToolMessage)).content


def test_question_with_ready_changes_is_not_interrupted(client, chat):
    chat([tool_message(call("propose_create_tag", {"tag": {"name": "Осень"}}, 1)), AIMessage(content="Добавить ещё тег «Вклад»?")])
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]
    reply = events(client.post(f"/chat/{sid}/messages", json={"text": "Создай тег Осень"}, headers=MANAGER))
    assert "confirmation_required" not in [kind for kind, _ in reply]


def test_suggestions_end_the_turn(client, chat):
    # После кнопок модель больше не вызывается: иначе она повторяла вопросы вторым сообщением.
    question = AIMessage(content="Когда начать показ?", tool_calls=[call("suggest_options", {"items": [{"label": "00:00 UTC", "value": "00:00"}, {"label": "09:00 UTC", "value": "09:00"}]}, 1)])
    model = chat([question, AIMessage(content="Начнём в 09:00.")])
    sid = client.post("/chat", json={}, headers=MANAGER).json()["sessionId"]
    reply = events(client.post(f"/chat/{sid}/messages", json={"text": "Вклад с 5 ноября"}, headers=MANAGER))
    assert [kind for kind, _ in reply if kind in {"suggestions", "done"}] == ["suggestions", "done"]
    assert len(model.seen) == 1
    events(client.post(f"/chat/{sid}/messages", json={"text": "09:00"}, headers=MANAGER))
    assert len(model.seen) == 2


def test_promo_image_for_saved_campaign_updates_content(client, chat):
    # У сохранённой кампании 101 смарт-баннер с иконкой: промо-экран получает её, баннер не меняется.
    chat(
        [
            tool_message(call("design_creative", {"brief": "Картинку на промо", "replaceBannerId": 201, "generateImage": True, "promoImageOnly": True}, 1)),
            AIMessage(content="Подготовил картинку для промо-экрана."),
            AIMessage(content="Сохранил."),
        ],
        [design_reply(BANNER_OK, 1)],
    )
    banner_image = client.get("/campaigns/101").json()["banners"][0]["content"]["image"]["url"]
    sid = client.post("/chat", json={"campaignId": 101}, headers=MANAGER).json()["sessionId"]
    reply = events(client.post(f"/chat/{sid}/messages", json={"text": "Добавь картинку на промо"}, headers=MANAGER))
    conf = next(data for kind, data in reply if kind == "confirmation_required")
    assert [op["kind"] for op in conf["operations"]] == ["update_content"]

    client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER)
    content = client.get("/campaigns/101").json()["contents"][0]["content"]
    image = next(c for c in content["component"]["components"] if c["role"] == "image")
    assert image["url"] == banner_image and image["aspectRatio"] == 1.0
