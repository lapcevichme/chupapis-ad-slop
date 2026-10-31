"""Картинки дизайн-агента: у сторис своя квадратная для промо-экрана, у смарт-баннера общая иконка."""

import asyncio

from app.infra.agent.designer import Designer, DesignRequest
from tests.test_agent import BANNER_OK, PROMO_OK, ScriptedModel, call, tool_message

STORY = {
    "id": 1,
    "code": "STORY",
    "titleMaxLength": 100,
    "textMaxLength": 500,
    "channels": ["iOS", "ANDROID"],
}
SMART = {
    "id": 2,
    "code": "SMART_BANNER",
    "titleMaxLength": 250,
    "textMaxLength": 1000,
    "channels": ["iOS", "ANDROID", "WEB"],
}


class FakeImages:
    def __init__(self):
        self.calls: list[tuple[str, str | None]] = []

    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        self.calls.append((prompt, size))
        return f"/api/media/{len(self.calls)}.png"


def design(banner_type) -> tuple[object, FakeImages]:
    args = {
        "bannerName": "Тест",
        "banner": BANNER_OK,
        "contentName": "Промо",
        "content": PROMO_OK,
        "imagePrompt": "banner background",
        "contentImagePrompt": "promo square",
    }
    images = FakeImages()
    designer = Designer(ScriptedModel(script=[tool_message(call("DesignResult", args, 1))]), images)
    outcome = asyncio.run(
        designer.design(DesignRequest("бриф", banner_type, with_content=True, generate_image=True))
    )
    return outcome, images


def test_story_gets_separate_square_promo_image():
    outcome, images = design(STORY)
    assert sorted(images.calls) == [
        ("banner background", "1024x1536"),
        ("promo square", "1024x1024"),
    ]
    promo_image = outcome.content["component"]["components"][0]
    assert promo_image["role"] == "image" and promo_image["aspectRatio"] == 1.0
    assert promo_image["url"] != outcome.banner["image"]["url"]


def test_smart_banner_reuses_square_icon():
    outcome, images = design(SMART)
    assert images.calls == [("banner background", "1024x1024")]
    promo_image = outcome.content["component"]["components"][0]
    assert (
        promo_image["url"] == outcome.banner["image"]["url"] and promo_image["aspectRatio"] == 1.0
    )


def test_edit_without_new_image_keeps_previous_one():
    previous = {"id": 217, "content": {**BANNER_OK, "image": {"url": "/api/media/old.png"}}}
    images = FakeImages()
    designer = Designer(
        ScriptedModel(
            script=[
                tool_message(call("DesignResult", {"bannerName": "Тест", "banner": BANNER_OK}, 1))
            ]
        ),
        images,
    )
    request = DesignRequest(
        "добавь срок", STORY, with_content=False, generate_image=False, previous=previous
    )
    outcome = asyncio.run(designer.design(request))
    assert images.calls == []
    assert outcome.banner["image"] == {"url": "/api/media/old.png"}


def test_promo_only_story_generates_just_the_square_image():
    previous = {"id": 217, "content": {**BANNER_OK, "image": {"url": "/api/media/old.png"}}}
    args = {
        "bannerName": "Тест",
        "banner": BANNER_OK,
        "imagePrompt": "ignored",
        "contentImagePrompt": "promo square",
    }
    images = FakeImages()
    designer = Designer(ScriptedModel(script=[tool_message(call("DesignResult", args, 1))]), images)
    request = DesignRequest(
        "картинку на промо",
        STORY,
        with_content=False,
        generate_image=True,
        previous=previous,
        content_image=True,
        promo_only=True,
    )
    outcome = asyncio.run(designer.design(request))
    assert images.calls == [("promo square", "1024x1024")]
    assert outcome.banner["image"] == {"url": "/api/media/old.png"}
    assert outcome.content_image == {"url": "/api/media/1.png", "aspectRatio": 1.0}
