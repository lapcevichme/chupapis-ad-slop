import asyncio
import base64
from typing import Any, Protocol

import httpx

from app.core.config import Settings

SPEECH_ATTEMPTS = 2
SPEECH_RETRY_DELAY = 1.0


class SpeechFailed(Exception):
    pass


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, audio_format: str) -> str:
        """Возвращает распознанный текст, для тишины — пустую строку."""


class Synthesizer(Protocol):
    async def synthesize(self, text: str) -> bytes:
        """Возвращает MP3."""


async def _post(
    settings: Settings,
    transport: httpx.AsyncBaseTransport | None,
    path: str,
    body: dict[str, Any],
) -> httpx.Response:
    # Пользователь ждёт ответа вживую: один быстрый повтор скрывает разовый сбой провайдера.
    failure = "Speech request did not run"
    async with httpx.AsyncClient(
        timeout=settings.speech_timeout_seconds, transport=transport
    ) as client:
        for attempt in range(SPEECH_ATTEMPTS):
            if attempt:
                await asyncio.sleep(SPEECH_RETRY_DELAY)
            try:
                response = await client.post(
                    f"{settings.llm_base_url}{path}",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=body,
                )
            except httpx.TransportError as exc:
                failure = f"Transport error: {type(exc).__name__}"
                continue
            if response.status_code == 429 or response.status_code >= 500:
                failure = f"HTTP {response.status_code}"
                continue
            if response.is_error:
                raise SpeechFailed(f"HTTP {response.status_code}")
            return response
    raise SpeechFailed(failure)


class OpenRouterTranscriber:
    """Base64 в JSON: этот формат OpenRouter описывает как основной для /audio/transcriptions."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def transcribe(self, audio: bytes, audio_format: str) -> str:
        body: dict[str, Any] = {
            "model": self.settings.stt_model,
            "input_audio": {"data": base64.b64encode(audio).decode(), "format": audio_format},
        }
        if self.settings.stt_language:
            body["language"] = self.settings.stt_language
        response = await _post(self.settings, self.transport, "/audio/transcriptions", body)
        try:
            text = response.json()["text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SpeechFailed("Unexpected transcription response") from exc
        if not isinstance(text, str):
            raise SpeechFailed("Unexpected transcription response")
        return text.strip()


class OpenRouterSynthesizer:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def synthesize(self, text: str) -> bytes:
        body = {
            "model": self.settings.tts_model,
            "voice": self.settings.tts_voice,
            "input": text,
            "response_format": "mp3",
        }
        response = await _post(self.settings, self.transport, "/audio/speech", body)
        if not response.content:
            raise SpeechFailed("Empty speech response")
        return response.content


def speech_transcriber(settings: Settings) -> Transcriber | None:
    if not settings.stt_model or not settings.llm_api_key:
        return None
    return OpenRouterTranscriber(settings)


def speech_synthesizer(settings: Settings) -> Synthesizer | None:
    if not settings.tts_model or not settings.llm_api_key:
        return None
    return OpenRouterSynthesizer(settings)
