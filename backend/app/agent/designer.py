"""Дизайн-агент: по задаче от чат-агента собирает JSON баннера и PROMO-контента.

Результат проверяется теми же схемами и правилами, что и в API (`app.domain.creatives`).
Ошибки возвращаются модели, и она исправляет JSON, пока он не пройдёт проверку.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field

from app.agent.llm import ImageGenerator
from app.agent.prompts import load_prompt
from app.domain.creatives import validate_banner_json, validate_content_json
from app.schemas.creative_json import BannerContent, PromoContent

MAX_ATTEMPTS = 3
# Сторис: картинка — фон всего экрана, текст поверх. Смарт-баннер: картинка — квадратная иконка в карточке.
IMAGE_SIZES = {"STORY": "1024x1536", "SMART_BANNER": "1024x1024"}


def image_aspect_ratio(type_code: str) -> float:
    """aspectRatio картинки на промо-экране (ширина / высота), как у кадра, который сгенерировали."""
    width, height = map(int, IMAGE_SIZES.get(type_code, "1024x1024").split("x"))
    return round(width / height, 2)


class DesignResult(BaseModel):
    """Готовый креатив. Тексты на русском, JSON строго по схемам."""

    bannerName: str = Field(description="Короткое служебное название баннера, до 100 символов")
    banner: BannerContent
    contentName: str | None = Field(None, description="Название промо-экрана; null, если экран не нужен")
    content: PromoContent | None = Field(None, description="PROMO-экран после тапа по баннеру; null, если не нужен")
    imagePrompt: str | None = Field(
        None, description="Промпт на английском для генерации картинки баннера: без людей и без текста на картинке"
    )


@dataclass
class DesignRequest:
    brief: str
    banner_type: dict[str, Any]
    with_content: bool
    generate_image: bool
    image_url: str | None = None
    previous: dict[str, Any] | None = None


@dataclass
class DesignOutcome:
    banner_name: str
    banner: dict[str, Any]
    content_name: str | None
    content: dict[str, Any] | None
    notes: list[str] = field(default_factory=list)


class DesignError(Exception):
    pass


def _validate(args: dict[str, Any], banner_type: dict[str, Any], with_content: bool) -> list[str]:
    _, errors = validate_banner_json(
        args.get("banner"),
        type_code=banner_type["code"],
        title_max=banner_type["titleMaxLength"],
        text_max=banner_type["textMaxLength"],
        prefix="banner",
    )
    problems = [f"{e.code} {e.field}: {e.message}" for e in errors]
    if not args.get("bannerName"):
        problems.append("bannerName обязателен")
    if with_content:
        if args.get("content") is None:
            problems.append("content обязателен: нужен промо-экран")
        else:
            _, content_errors = validate_content_json(args["content"], prefix="content")
            problems += [f"{e.code} {e.field}: {e.message}" for e in content_errors]
    return problems


class Designer:
    def __init__(self, model: BaseChatModel, images: ImageGenerator):
        # Без принудительного tool_choice: часть моделей (в том числе Claude 5.5) его не поддерживает.
        self.model = model.bind_tools([DesignResult])
        self.images = images

    async def design(self, request: DesignRequest, progress: Callable[[str], None] = lambda _: None) -> DesignOutcome:
        t = request.banner_type
        task = {
            "brief": request.brief,
            "bannerType": t["code"],
            "titleMaxLength": t["titleMaxLength"],
            "textMaxLength": t["textMaxLength"],
            "withContent": request.with_content,
            "needImagePrompt": request.generate_image,
            "imageSize": IMAGE_SIZES.get(t["code"]) if request.generate_image else None,
            "previousVersion": request.previous,
        }
        messages: list = [SystemMessage(load_prompt("design")), HumanMessage(json.dumps(task, ensure_ascii=False))]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            progress(f"Дизайнер собирает креатив, попытка {attempt}")
            response: AIMessage = await self.model.ainvoke(messages)
            call = next((c for c in response.tool_calls if c["name"] == "DesignResult"), None)
            if call is None:
                problems = ["модель ответила текстом вместо вызова DesignResult"]
                messages += [response, HumanMessage("Верни результат только вызовом инструмента DesignResult.")]
                continue
            problems = _validate(call["args"], t, request.with_content)
            if not problems:
                return await self._finish(call["args"], request, progress)
            messages += [
                response,
                ToolMessage(
                    tool_call_id=call["id"],
                    content="JSON не прошёл проверку, исправь и верни заново:\n" + "\n".join(problems),
                ),
            ]
        raise DesignError("Не удалось собрать валидный JSON: " + "; ".join(problems))

    async def _finish(self, args: dict[str, Any], request: DesignRequest, progress) -> DesignOutcome:
        banner = BannerContent.model_validate(args["banner"]).model_dump(mode="json", exclude_none=True)
        content = None
        if request.with_content and args.get("content"):
            content = PromoContent.model_validate(args["content"]).model_dump(mode="json", exclude_none=True)
        notes: list[str] = []

        url = request.image_url
        if url is None and request.generate_image and args.get("imagePrompt"):
            progress("Генерирую картинку")
            try:
                url = await self.images.generate(args["imagePrompt"], IMAGE_SIZES.get(request.banner_type["code"]))
            except Exception as exc:  # генерация — бонус, сценарий без неё не ломается
                notes.append(f"Картинку сгенерировать не удалось ({type(exc).__name__}), баннер без изображения")
            else:
                if url is None:
                    notes.append("Генерация картинок недоступна, баннер без изображения")
        if url:
            banner["image"] = {"url": url}
            components = content["component"]["components"] if content else None
            if components is not None and len(components) < 6 and not any(c["role"] == "image" for c in components):
                components.insert(0, {"role": "image", "url": url, "aspectRatio": image_aspect_ratio(request.banner_type["code"])})
        return DesignOutcome(args["bannerName"][:100], banner, (args.get("contentName") or "Промо-экран")[:100] if content else None, content, notes)
