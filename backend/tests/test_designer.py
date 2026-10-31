"""Картинки дизайн-агента: у сторис своя квадратная для промо-экрана, у смарт-баннера общая иконка."""

import asyncio

import pytest

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


# Квадрат над текстом занимал почти половину экрана, и промо-экран не влезал без прокрутки.
def test_story_promo_gets_own_wide_image():
    outcome, images = design(STORY)
    assert images.calls == [("banner background", "1024x1536"), ("promo square", "1536x1024")]
    promo_image = outcome.content["component"]["components"][0]
    assert promo_image["role"] == "image" and promo_image["aspectRatio"] == 1.5
    assert promo_image["url"] != outcome.banner["image"]["url"]


# Картинка смарт-баннера — фон всей карточки, а не иконка 64×64.
def test_smart_banner_gets_card_background_and_own_promo_image():
    outcome, images = design(SMART)
    assert images.calls == [("banner background", "1536x1024"), ("promo square", "1536x1024")]
    promo_image = outcome.content["component"]["components"][0]
    assert (
        promo_image["url"] != outcome.banner["image"]["url"] and promo_image["aspectRatio"] == 1.5
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


LONG_STORY = {
    **BANNER_OK,
    "title": "Сказки на ночь от ИИ-единорога — $99 в месяц",
    "text": "Добрый единорог расскажет вашему малышу сказку и подарит тёплый вечер всей семье. Акция с 14 по 31 декабря 2026.",
    "titleStyle": {"fontSize": 32, "fontWeight": "bold", "textColor": "#FFFFFFFF"},
    "textStyle": {"fontSize": 18, "fontWeight": "regular", "textColor": "#FFFFFFFF"},
}


def run_story_design(banners: list[dict], banner_type=STORY, generate_image=True):
    script = [
        tool_message(
            call(
                "DesignResult", {"bannerName": "Тест", "banner": banner, "imagePrompt": "bg"}, index
            )
        )
        for index, banner in enumerate(banners)
    ]
    request = DesignRequest(
        "бриф", banner_type, with_content=False, generate_image=generate_image, content_image=False
    )
    return asyncio.run(Designer(ScriptedModel(script=script), FakeImages()).design(request))


def test_long_story_text_over_image_is_sent_back_for_shortening():
    outcome = run_story_design([LONG_STORY, BANNER_OK])
    assert outcome.banner["title"] == BANNER_OK["title"]


def test_long_story_text_never_fails_the_creative():
    outcome = run_story_design([LONG_STORY, LONG_STORY, LONG_STORY])
    assert outcome.banner["title"] == LONG_STORY["title"]


def test_long_text_is_fine_without_story_image():
    outcome = run_story_design([LONG_STORY], generate_image=False)
    assert outcome.banner["title"] == LONG_STORY["title"]


def test_long_text_is_fine_in_smart_banner():
    outcome = run_story_design([LONG_STORY], banner_type=SMART)
    assert outcome.banner["title"] == LONG_STORY["title"]


def test_promo_only_generates_just_the_promo_image():
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
    assert images.calls == [("promo square", "1536x1024")]
    assert outcome.banner["image"] == {"url": "/api/media/old.png"}
    assert outcome.content_image == {"url": "/api/media/1.png", "aspectRatio": 1.5}


def design_layout(layout: str) -> tuple[object, FakeImages]:
    args = {
        "bannerName": "Тест",
        "banner": BANNER_OK,
        "content": PROMO_OK,
        "imagePrompt": "banner background",
        "contentImagePrompt": "promo picture",
        "promoLayout": layout,
    }
    images = FakeImages()
    designer = Designer(ScriptedModel(script=[tool_message(call("DesignResult", args, 1))]), images)
    outcome = asyncio.run(
        designer.design(DesignRequest("бриф", SMART, with_content=True, generate_image=True))
    )
    return outcome, images


@pytest.mark.parametrize("layout", ["number", "benefits", "premium"])
def test_layouts_without_promo_image_skip_its_generation(layout):
    # Картинки в этих раскладках нет: лишний вызов gpt-image стоит денег и ломает композицию.
    outcome, images = design_layout(layout)
    assert images.calls == [("banner background", "1536x1024")]
    assert all(c["role"] != "image" for c in outcome.content["component"]["components"])


def test_color_layout_gets_square_image_on_top():
    outcome, images = design_layout("color")
    assert images.calls[-1] == ("promo picture", "1024x1024")
    first = outcome.content["component"]["components"][0]
    assert first["role"] == "image" and first["aspectRatio"] == 1.0


def test_split_layout_puts_image_before_buttons():
    outcome, _ = design_layout("split")
    roles = [c["role"] for c in outcome.content["component"]["components"]]
    assert roles == ["text", "image", "button"]
