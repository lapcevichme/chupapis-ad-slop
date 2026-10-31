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
    async def generate(self, prompt: str) -> str | None:
        """Возвращает ссылку на картинку или None, если сгенерировать не удалось."""


class OpenRouterImageGenerator:
    """Картинка через chat completions с modalities=["image"]: модель отдаёт data URL, бэкенд сохраняет файл в /media."""

    def __init__(self, model: str):
        self.model = model

    async def generate(self, prompt: str) -> str | None:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": self.model,
                    "modalities": ["image", "text"],
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
        images = response.json()["choices"][0]["message"].get("images") or []
        if not images:
            return None
        header, _, data = images[0]["image_url"]["url"].partition(",")
        extension = "jpg" if "jpeg" in header else "png"
        name = f"{uuid.uuid4().hex}.{extension}"
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        (settings.media_dir / name).write_bytes(base64.b64decode(data))
        return f"{settings.media_base_url}/{name}"


class NoImageGenerator:
    async def generate(self, prompt: str) -> str | None:
        return None


def image_generator() -> ImageGenerator:
    if not settings.image_model or not settings.llm_api_key:
        return NoImageGenerator()
    return OpenRouterImageGenerator(settings.image_model)
