"""Фон-паттерн в SVG: проверка ответа модели, повтор после ошибки, стиль картинки и запасной вариант."""

import asyncio

import pytest
from langchain_core.messages import AIMessage

from app.agent.designer import Designer, DesignRequest
from app.agent.patterns import SvgPatternGenerator, SvgRejected, clean_svg
from app.config import settings
from tests.test_agent import BANNER_OK, ScriptedModel, call, tool_message
from tests.test_designer import STORY, FakeImages

GOOD = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><defs><pattern id="p" width="40" height="40" '
    'patternUnits="userSpaceOnUse"><circle cx="20" cy="20" r="6" fill="#2A6B47"/></pattern></defs>'
    '<rect width="100%" height="100%" fill="#1F5E3B"/><rect width="100%" height="100%" fill="url(#p)"/></svg>'
)


def test_clean_svg_sets_size_and_keeps_pattern():
    svg = clean_svg("Вот фон:\n" + GOOD.replace(' xmlns="http://www.w3.org/2000/svg"', ""), 1080, 1920)
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert 'width="1080"' in svg and 'viewBox="0 0 1080 1920"' in svg and "<pattern" in svg


@pytest.mark.parametrize(
    "bad",
    [
        GOOD.replace("</svg>", "<script>alert(1)</script></svg>"),
        GOOD.replace('<circle cx="20"', '<circle onclick="x()" cx="20"'),
        GOOD.replace('fill="url(#p)"', 'fill="url(https://evil.example/p.svg)"'),
        GOOD.replace("</svg>", '<image href="https://evil.example/x.png"/></svg>'),
        GOOD.replace("</defs>", "</defs><text>16%</text>"),
        GOOD[:-6],
    ],
)
def test_clean_svg_rejects_unsafe_or_broken(bad):
    with pytest.raises(SvgRejected):
        clean_svg(bad, 1080, 1920)


@pytest.fixture
def media(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    return tmp_path


def test_generator_retries_broken_svg(media):
    model = ScriptedModel(script=[AIMessage(content=GOOD[:-6]), AIMessage(content=GOOD)])
    url = asyncio.run(SvgPatternGenerator(model).generate(theme="Вклад", kind="STORY", base_color="#1F5E3B", text_color="#FFFFFF", size="1080x1920"))
    assert url.startswith("/api/media/") and url.endswith(".svg")
    assert (media / url.rsplit("/", 1)[-1]).read_text(encoding="utf-8").startswith("<svg")
    assert "SVG rejected" in model.seen[-1][-1].content


class FakePatterns:
    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []

    async def generate(self, *, theme, kind, base_color, text_color, size):
        self.calls.append((kind, base_color, size))
        return f"/api/media/pattern-{len(self.calls)}.svg"


class FailingImages(FakeImages):
    async def generate(self, prompt, size=None):
        raise RuntimeError("limit")


def _design(images, patterns, style: str):
    args = {"bannerName": "Тест", "banner": BANNER_OK, "imagePrompt": "piggy", "contentImagePrompt": "piggy square"}
    designer = Designer(ScriptedModel(script=[tool_message(call("DesignResult", args, 1))]), images, patterns)
    request = DesignRequest("Вклад 16%", STORY, with_content=False, generate_image=True, image_style=style)
    return asyncio.run(designer.design(request))


def test_pattern_style_skips_illustration():
    images, patterns = FakeImages(), FakePatterns()
    outcome = _design(images, patterns, "pattern")
    assert images.calls == []
    # Цвет фона баннера без альфа-канала: модель паттерна строит палитру от него.
    assert patterns.calls == [("STORY", "#21A038", "1024x1536")]
    assert outcome.banner["image"] == {"url": "/api/media/pattern-1.svg"}


def test_failed_illustration_falls_back_to_pattern():
    patterns = FakePatterns()
    outcome = _design(FailingImages(), patterns, "illustration")
    assert outcome.banner["image"] == {"url": "/api/media/pattern-1.svg"}
    assert any("вместо неё фон-паттерн" in note for note in outcome.notes)
