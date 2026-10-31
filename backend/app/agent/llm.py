"""Слой над провайдером LLM. Логика агента видит только `BaseChatModel` и `ImageGenerator`."""

import base64
import uuid
from typing import Protocol

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings


def chat_model(model: str, *, temperature: float = 0.3) -> BaseChatModel:
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "missing-key",
        temperature=temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=2,
    )


class ImageGenerator(Protocol):
    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        """Возвращает ссылку на картинку или None, если сгенерировать не удалось. size — "ШxВ"."""


class OpenRouterImageGenerator:
    """Картинка через OpenAI-совместимый /images/generations. Бэкенд сохраняет файл в /media и отдаёт ссылку."""

    def __init__(self, model: str):
        self.model = model

    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        body = {"model": self.model, "prompt": prompt} | ({"size": size} if size else {})
        # Один повтор: соединение с провайдером картинок иногда рвётся (httpx.ReadError).
        transport = httpx.AsyncHTTPTransport(retries=1)
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds, transport=transport) as client:
            for attempt in range(2):
                try:
                    response = await client.post(
                        f"{settings.llm_base_url}/images/generations",
                        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                        json=body,
                    )
                    break
                except httpx.TransportError:
                    if attempt == 1:
                        raise
            response.raise_for_status()
        data = response.json().get("data") or []
        if not data or not data[0].get("b64_json"):
            return None
        raw = base64.b64decode(data[0]["b64_json"])
        extension = "jpg" if raw[:2] == b"\xff\xd8" else "png"
        name = f"{uuid.uuid4().hex}.{extension}"
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        (settings.media_dir / name).write_bytes(raw)
        return f"{settings.media_base_url}/{name}"


class NoImageGenerator:
    async def generate(self, prompt: str, size: str | None = None) -> str | None:
        return None


def image_generator() -> ImageGenerator:
    if not settings.image_model or not settings.llm_api_key:
        return NoImageGenerator()
    return OpenRouterImageGenerator(settings.image_model)
