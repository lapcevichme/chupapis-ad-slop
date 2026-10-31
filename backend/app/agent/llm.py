"""Слой над провайдером LLM. Логика агента видит только `BaseChatModel` и `ImageGenerator`."""

import asyncio
import base64
import uuid
from typing import Protocol

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings

# 4 попытки генерации картинки, паузы между ними 2, 4 и 8 секунд.
IMAGE_ATTEMPTS = 4
IMAGE_RETRY_DELAYS = (2, 4, 8)


def chat_model(model: str, *, temperature: float = 0.3) -> BaseChatModel:
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "missing-key",
        temperature=temperature,
        timeout=settings.llm_timeout_seconds,
        # SDK OpenAI сам повторяет сетевые сбои, 429 и 5xx с экспоненциальной паузой: 1 + 3 повтора.
        max_retries=3,
    )


class ImageGenerator(Protocol):
    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        """Возвращает ссылку на картинку или None, если сгенерировать не удалось. size — "ШxВ"."""


class OpenRouterImageGenerator:
    """Картинка через OpenAI-совместимый /images/generations. Бэкенд сохраняет файл в /media и отдаёт ссылку."""

    def __init__(self, model: str, transport: httpx.AsyncBaseTransport | None = None):
        self.model = model
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
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        (settings.media_dir / name).write_bytes(raw)
        return f"{settings.media_base_url}/{name}"

    async def _post_with_retries(self, body: dict) -> httpx.Response:
        """Сетевые сбои, 429 и 5xx повторяем с растущей паузой; остальные 4xx — ошибка запроса, повторять бессмысленно."""
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds, transport=self.transport) as client:
            for attempt in range(IMAGE_ATTEMPTS):
                if attempt:
                    await asyncio.sleep(IMAGE_RETRY_DELAYS[attempt - 1])
                try:
                    response = await client.post(
                        f"{settings.llm_base_url}/images/generations",
                        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                        json=body,
                    )
                except httpx.TransportError as exc:
                    last_error = exc
                    continue
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)
                    continue
                response.raise_for_status()
                return response
        raise last_error


class NoImageGenerator:
    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        return None


def image_generator() -> ImageGenerator:
    if not settings.image_model or not settings.llm_api_key:
        return NoImageGenerator()
    return OpenRouterImageGenerator(settings.image_model)
