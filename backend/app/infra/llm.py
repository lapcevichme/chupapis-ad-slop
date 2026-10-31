"""Слой над провайдером LLM. Логика агента видит только `BaseChatModel` и `ImageGenerator`."""

import asyncio
import base64
import uuid
from typing import Protocol

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import Settings

# 4 попытки генерации картинки, паузы между ними 2, 4 и 8 секунд.
IMAGE_ATTEMPTS = 4
IMAGE_RETRY_DELAYS = (2, 4, 8)


def chat_model(settings: Settings, model: str, *, temperature: float = 0.3) -> BaseChatModel:
    providers = [p.strip() for p in settings.llm_providers.split(",") if p.strip()]
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "missing-key",
        temperature=temperature,
        timeout=settings.llm_timeout_seconds,
        # SDK OpenAI сам повторяет сетевые сбои, 429 и 5xx с экспоненциальной паузой: 1 + 3 повтора.
        max_retries=3,
        # Всегда сначала один и тот же провайдер, чтобы попадать в его кеш. Запасной — только если он упал.
        extra_body={"provider": {"order": providers, "allow_fallbacks": True}}
        if providers
        else None,
    )


CACHE_CONTROL = {"type": "ephemeral"}


def _text_of(message: BaseMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    return "".join(
        block.get("text", "")
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def _mark(message: BaseMessage) -> BaseMessage:
    """Копия сообщения, у которой последний текстовый блок помечен точкой кеша. В истории диалога ничего не меняется."""
    if isinstance(message.content, str):
        content = [{"type": "text", "text": message.content, "cache_control": CACHE_CONTROL}]
    else:
        content = [dict(block) for block in message.content]
        last = max(
            i
            for i, block in enumerate(content)
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
        )
        content[last]["cache_control"] = CACHE_CONTROL
    return message.model_copy(update={"content": content})


def with_cache_breakpoints(
    messages: list[BaseMessage], stable: int, *, enabled: bool = True
) -> list[BaseMessage]:
    """Точки кеша Anthropic: на первом сообщении (системный промпт, перед ним в кеш попадают инструменты)
    и на последнем непустом из первых `stable` сообщений — это история, которая между шагами только растёт.
    Всё после `stable` меняется каждый шаг и в кеш не идёт.
    """
    if not enabled or not messages:
        return messages
    result = list(messages)
    marks = {0} | {
        next(
            (i for i in range(min(stable, len(result)) - 1, 0, -1) if _text_of(result[i]).strip()),
            0,
        )
    }
    for i in marks:
        if _text_of(result[i]).strip():
            result[i] = _mark(result[i])
    return result


class ImageGenerator(Protocol):
    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        """Возвращает ссылку на картинку или None, если сгенерировать не удалось. size — "ШxВ"."""


class OpenRouterImageGenerator:
    """Картинка через OpenAI-совместимый /images/generations. Бэкенд сохраняет файл в /media и отдаёт ссылку."""

    def __init__(
        self, model: str, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ):
        self.model = model
        self.settings = settings
        self.transport = transport

    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        body = {"model": self.model, "prompt": prompt} | ({"size": size} if size else {})
        response = await self._post_with_retries(body)
        data = response.json().get("data") or []
        if not data or not data[0].get("b64_json"):
            return None
        raw = base64.b64decode(data[0]["b64_json"])
        extension = "jpg" if raw[:2] == b"\xff\xd8" else "png"
        name = f"{uuid.uuid4().hex}.{extension}"
        self.settings.media_dir.mkdir(parents=True, exist_ok=True)
        (self.settings.media_dir / name).write_bytes(raw)
        return f"{self.settings.media_base_url}/{name}"

    async def _post_with_retries(self, body: dict) -> httpx.Response:
        """Сетевые сбои, 429 и 5xx повторяем с растущей паузой; остальные 4xx — ошибка запроса, повторять бессмысленно."""
        last_error: Exception | None = None
        async with httpx.AsyncClient(
            timeout=self.settings.llm_timeout_seconds, transport=self.transport
        ) as client:
            for attempt in range(IMAGE_ATTEMPTS):
                if attempt:
                    await asyncio.sleep(IMAGE_RETRY_DELAYS[attempt - 1])
                try:
                    response = await client.post(
                        f"{self.settings.llm_base_url}/images/generations",
                        headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                        json=body,
                    )
                except httpx.TransportError as exc:
                    last_error = exc
                    continue
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = httpx.HTTPStatusError(
                        f"HTTP {response.status_code}", request=response.request, response=response
                    )
                    continue
                response.raise_for_status()
                return response
        raise last_error


class NoImageGenerator:
    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        return None


def image_generator(settings: Settings) -> ImageGenerator:
    if not settings.image_model or not settings.llm_api_key:
        return NoImageGenerator()
    return OpenRouterImageGenerator(settings.image_model, settings)
