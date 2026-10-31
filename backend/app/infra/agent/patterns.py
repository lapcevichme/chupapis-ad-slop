"""Фон-паттерн для баннера: LLM рисует SVG, тема передаётся только цветом.

Дешёвая альтернатива растровой иллюстрации и её запасной вариант. Ответ модели проверяется как XML и по белому
списку тегов и атрибутов: при ошибке модель исправляет SVG, до трёх попыток.
"""

import json
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.infra.agent.prompts import load_prompt
from app.infra.llm import _text_of, with_cache_breakpoints

MAX_ATTEMPTS = 3
SVG_NS = "http://www.w3.org/2000/svg"
ALLOWED_TAGS = {
    "svg",
    "defs",
    "pattern",
    "rect",
    "circle",
    "ellipse",
    "line",
    "path",
    "polygon",
    "polyline",
    "g",
}
_SVG = re.compile(r"<svg\b.*</svg>", re.S)


class SvgRejected(ValueError):
    pass


def clean_svg(text: str, width: int, height: int) -> str:
    """Проверенный SVG заданного размера. Скрипты, обработчики событий и внешние ссылки не пропускаем."""
    match = _SVG.search(text)
    if not match:
        raise SvgRejected("в ответе нет <svg>…</svg>")
    raw = match.group(0)
    if "<!DOCTYPE" in raw or "<!ENTITY" in raw:
        raise SvgRejected("DOCTYPE и ENTITY запрещены")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SvgRejected(f"невалидный XML: {exc}") from exc
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag not in ALLOWED_TAGS:
            raise SvgRejected(f"тег <{tag}> не разрешён")
        for name, value in element.attrib.items():
            local = name.rsplit("}", 1)[-1]
            if local.startswith("on"):
                raise SvgRejected(f"атрибут {local} запрещён")
            if local == "href" and not value.startswith("#"):
                raise SvgRejected("внешние ссылки запрещены")
            if "url(" in value and not re.fullmatch(r"\s*url\(#[\w-]+\)\s*", value):
                raise SvgRejected("в url() разрешены только ссылки внутри файла")
    # Размер задаём сами, xmlns обязателен: без него браузер не покажет SVG в <img>.
    root.set("width", str(width))
    root.set("height", str(height))
    root.set("viewBox", f"0 0 {width} {height}")
    if not root.tag.startswith("{"):
        root.set("xmlns", SVG_NS)
    ET.register_namespace("", SVG_NS)
    return ET.tostring(root, encoding="unicode")


class SvgPatternGenerator:
    def __init__(
        self,
        model: BaseChatModel,
        *,
        media_dir: Path,
        media_base_url: str = "/api/media",
        cache_enabled: bool = True,
    ):
        self.model = model
        self.media_dir = media_dir
        self.media_base_url = media_base_url
        self.cache_enabled = cache_enabled

    async def generate(
        self, *, theme: str, kind: str, base_color: str, text_color: str, size: str
    ) -> str | None:
        """kind — STORY (фон сторис), CARD (фон карточки смарт-баннера) или WIDE (полоса над текстом промо-экрана)."""
        width, height = (int(v) for v in size.split("x"))
        task = {
            "kind": kind,
            "theme": theme,
            "baseColor": base_color,
            "textColor": text_color,
            "canvas": {"width": width, "height": height, "viewBox": f"0 0 {width} {height}"},
        }
        messages: list[BaseMessage] = [
            SystemMessage(load_prompt("pattern")),
            HumanMessage(json.dumps(task, ensure_ascii=False)),
        ]
        for _ in range(MAX_ATTEMPTS):
            response: AIMessage = await self.model.ainvoke(
                with_cache_breakpoints(messages, stable=1, enabled=self.cache_enabled)
            )
            try:
                svg = clean_svg(_text_of(response), width, height)
            except SvgRejected as exc:
                messages += [
                    response,
                    HumanMessage(f"SVG rejected: {exc}. Return the full corrected SVG."),
                ]
                continue
            name = f"{uuid.uuid4().hex}.svg"
            self.media_dir.mkdir(parents=True, exist_ok=True)
            (self.media_dir / name).write_text(svg, encoding="utf-8")
            return f"{self.media_base_url}/{name}"
        return None
