import asyncio
import base64
from typing import Protocol

import httpx

from app.core.config import Settings

TRANSCRIBE_ATTEMPTS = 2
TRANSCRIBE_RETRY_DELAY = 1.0


class TranscriptionFailed(Exception):
    pass


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, audio_format: str) -> str:
        """Возвращает распознанный текст, для тишины — пустую строку."""


class OpenRouterTranscriber:
    """Base64 в JSON: этот формат OpenRouter описывает как основной для /audio/transcriptions."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def transcribe(self, audio: bytes, audio_format: str) -> str:
        body: dict[str, object] = {
            "model": self.settings.stt_model,
            "input_audio": {"data": base64.b64encode(audio).decode(), "format": audio_format},
        }
        if self.settings.stt_language:
            body["language"] = self.settings.stt_language
        response = await self._post(body)
        try:
            text = response.json()["text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise TranscriptionFailed("Unexpected transcription response") from exc
        if not isinstance(text, str):
            raise TranscriptionFailed("Unexpected transcription response")
        return text.strip()

    async def _post(self, body: dict[str, object]) -> httpx.Response:
        # Запись живёт только в этом запросе: при разовом сбое пользователю пришлось бы говорить заново.
        failure = "Transcription did not run"
        async with httpx.AsyncClient(
            timeout=self.settings.stt_timeout_seconds, transport=self.transport
        ) as client:
            for attempt in range(TRANSCRIBE_ATTEMPTS):
                if attempt:
                    await asyncio.sleep(TRANSCRIBE_RETRY_DELAY)
                try:
                    response = await client.post(
                        f"{self.settings.llm_base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                        json=body,
                    )
                except httpx.TransportError as exc:
                    failure = f"Transport error: {type(exc).__name__}"
                    continue
                if response.status_code == 429 or response.status_code >= 500:
                    failure = f"HTTP {response.status_code}"
                    continue
                if response.is_error:
                    raise TranscriptionFailed(f"HTTP {response.status_code}")
                return response
        raise TranscriptionFailed(failure)


def speech_transcriber(settings: Settings) -> Transcriber | None:
    if not settings.stt_model or not settings.llm_api_key:
        return None
    return OpenRouterTranscriber(settings)
