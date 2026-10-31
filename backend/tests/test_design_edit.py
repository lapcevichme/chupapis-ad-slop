"""Точечная правка готового креатива: дизайнер меняет только то, что просили, остальное остаётся как было."""

import asyncio

import pytest
from langchain_core.messages import AIMessage

from app.infra.agent.designer import Designer, EditRequest, PatchError, apply_changes
from tests import test_agent
from tests.test_agent import BANNER_OK, MANAGER, PROMO_OK, ScriptedModel, call, events, tool_message
from tests.test_designer import SMART, FakeImages
from tests.test_patterns import FakePatterns

# Фикстура чата живёт в test_agent: регистрируем её и здесь.
chat = test_agent.chat

DOC = {"banner": BANNER_OK, "content": PROMO_OK}


def test_changes_touch_only_given_paths():
    edited = apply_changes(
        DOC,
        [
            {"op": "set", "path": "/banner/title", "value": "Вклад под 18%"},
            {"op": "set", "path": "/banner/textStyle/textColor", "value": "#FFFFFFFF"},
            {
                "op": "insert",
                "path": "/content/component/components/-",
                "value": {"role": "text", "format": "none", "text": "До 31 декабря"},
            },
        ],
    )
    assert edited["banner"] == {
        **BANNER_OK,
        "title": "Вклад под 18%",
        "textStyle": {"textColor": "#FFFFFFFF"},
    }
    assert edited["content"]["component"]["components"][:-1] == PROMO_OK["component"]["components"]
    assert DOC["banner"]["title"] == "Вклад под 16% годовых"


@pytest.mark.parametrize(
    "change",
    [
        {"op": "set", "path": "/banner/image/url", "value": "https://x"},
        {"op": "remove", "path": "/banner/nope"},
        {"op": "set", "path": "/content/component/components/9/text", "value": "x"},
        {"op": "set", "path": "/title", "value": "x"},
    ],
)
def test_bad_changes_are_explained(change):
    with pytest.raises(PatchError):
        apply_changes(DOC, [change])


def edit(changes, banner, *, patterns=None, content=None, script_extra=()):
    args = {"changes": changes, "summary": "поменял заголовок"}
    model = ScriptedModel(script=[*script_extra, tool_message(call("DesignEdit", args, 1))])
    designer = Designer(model, FakeImages(), patterns)
    request = EditRequest(
        "заголовок про 18%", SMART, "Смарт", banner, content=content, image_style="mixed"
    )
    return asyncio.run(designer.edit(request)), model


def test_edit_keeps_everything_else_and_the_image():
    banner = {**BANNER_OK, "image": {"url": "/api/media/old.svg"}, "buttonName": "Открыть"}
    patterns = FakePatterns()
    outcome, _ = edit(
        [{"op": "set", "path": "/banner/title", "value": "Вклад под 18%"}],
        banner,
        patterns=patterns,
    )
    assert outcome.banner == {**banner, "title": "Вклад под 18%"}
    assert outcome.summary == "поменял заголовок" and patterns.calls == []


def test_new_colors_repaint_the_pattern_background():
    banner = {**BANNER_OK, "image": {"url": "/api/media/old.svg"}}
    patterns = FakePatterns()
    outcome, _ = edit(
        [{"op": "set", "path": "/banner/background/color", "value": "#0B3D91FF"}],
        banner,
        patterns=patterns,
    )
    assert patterns.calls == [("CARD", "#0B3D91", "1536x1024")]
    assert outcome.banner["image"] == {"url": "/api/media/pattern-1.svg"}


def test_broken_edit_goes_back_to_the_model():
    bad = tool_message(
        call(
            "DesignEdit",
            {
                "changes": [{"op": "set", "path": "/banner/title", "value": "x" * 300}],
                "summary": "?",
            },
            1,
        )
    )
    outcome, model = edit(
        [{"op": "set", "path": "/banner/title", "value": "Вклад под 18%"}],
        BANNER_OK,
        script_extra=[bad],
    )
    assert outcome.banner["title"] == "Вклад под 18%"
    assert "не применилась" in model.seen[-1][-1].content


def test_edit_of_saved_banner_proposes_only_the_changed_objects(client, chat):
    # Сохранённая кампания 101: правка заголовка не трогает промо-экран и остальные поля баннера.
    chat(
        [
            tool_message(
                call("design_creative", {"brief": "Заголовок короче", "replaceBannerId": 201}, 1)
            ),
            AIMessage(content="Сократил заголовок."),
            AIMessage(content="Сохранил."),
        ],
        [
            tool_message(
                call(
                    "DesignEdit",
                    {
                        "changes": [
                            {"op": "set", "path": "/banner/title", "value": "Короткий заголовок"}
                        ],
                        "summary": "сократил заголовок",
                    },
                    1,
                )
            )
        ],
    )
    before = client.get("/campaigns/101").json()["banners"][0]
    sid = client.post("/chat", json={"campaignId": 101}, headers=MANAGER).json()["sessionId"]
    reply = events(
        client.post(
            f"/chat/{sid}/messages", json={"text": "Сделай заголовок короче"}, headers=MANAGER
        )
    )
    conf = next(data for kind, data in reply if kind == "confirmation_required")
    assert [op["kind"] for op in conf["operations"]] == ["update_banner"]

    client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER)
    after = client.get("/campaigns/101").json()["banners"][0]
    assert after["content"] == {**before["content"], "title": "Короткий заголовок"}
    assert after["name"] == before["name"]


def test_second_edit_of_saved_banner_replaces_the_first_operation(client, chat):
    # Обе правки попадают в одну операцию: PUT заменяет баннер целиком, вторая строится поверх первой.
    def edit_call(path, value, n):
        changes = [{"op": "set", "path": path, "value": value}]
        return tool_message(call("DesignEdit", {"changes": changes, "summary": "правка"}, n))

    chat(
        [
            tool_message(
                call("design_creative", {"brief": "Фон синий", "replaceBannerId": 201}, 1)
            ),
            tool_message(
                call("design_creative", {"brief": "Заголовок короче", "replaceBannerId": 201}, 2)
            ),
            AIMessage(content="Поправил."),
            AIMessage(content="Сохранил."),
        ],
        [
            edit_call("/banner/background/color", "#0B3D91FF", 1),
            edit_call("/banner/title", "Короткий заголовок", 2),
        ],
    )
    before = client.get("/campaigns/101").json()["banners"][0]
    sid = client.post("/chat", json={"campaignId": 101}, headers=MANAGER).json()["sessionId"]
    reply = events(
        client.post(f"/chat/{sid}/messages", json={"text": "Синий фон и короче"}, headers=MANAGER)
    )
    conf = next(data for kind, data in reply if kind == "confirmation_required")
    assert [op["kind"] for op in conf["operations"]] == ["update_banner"]

    client.post(f"/chat/{sid}/confirmations/{conf['id']}", json={"approved": True}, headers=MANAGER)
    after = client.get("/campaigns/101").json()["banners"][0]["content"]
    assert after["title"] == "Короткий заголовок"
    assert after["background"]["color"] == "#0B3D91FF"
    assert after["text"] == before["content"]["text"]
