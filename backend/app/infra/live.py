from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings
from app.infra.agent.prompts import load_prompt


class LiveSessionFailed(Exception):
    pass


@dataclass(frozen=True)
class LiveSessionStarted:
    session_id: str
    answer_sdp: str


class LiveSessions(Protocol):
    async def create(self, offer_sdp: str) -> LiveSessionStarted:
        """Создаёт сессию по SDP-предложению браузера."""


class OpenAILiveSessions:
    """Ключ и настройка сессии остаются на сервере, браузер получает только SDP-ответ."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def create(self, offer_sdp: str) -> LiveSessionStarted:
        body = {
            "session": {
                "model": self.settings.live_model,
                "instructions": load_prompt("voice_live"),
                "audio": {"output": {"voice": self.settings.live_voice}},
                # Думает и пишет прежний агент: у него проверки и карточки подтверждения.
                "delegation": {"type": "client"},
            },
            "transport": {"type": "webrtc", "sdp": offer_sdp},
        }
        # Без повтора: каждая созданная сессия оплачивается, а запасной путь есть у клиента.
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.speech_timeout_seconds, transport=self.transport
            ) as client:
                response = await client.post(
                    f"{self.settings.live_base_url}/live/sessions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json=body,
                )
        except httpx.TransportError as exc:
            raise LiveSessionFailed(f"Transport error: {type(exc).__name__}") from exc
        if response.is_error:
            raise LiveSessionFailed(f"HTTP {response.status_code}")
        try:
            payload = response.json()
            session_id = payload["session"]["id"]
            answer_sdp = payload["transport"]["sdp"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LiveSessionFailed("Unexpected live session response") from exc
        if not (isinstance(session_id, str) and isinstance(answer_sdp, str) and answer_sdp):
            raise LiveSessionFailed("Unexpected live session response")
        return LiveSessionStarted(session_id=session_id, answer_sdp=answer_sdp)


def live_sessions(settings: Settings) -> LiveSessions | None:
    if not settings.live_model or not settings.openai_api_key:
        return None
    return OpenAILiveSessions(settings)
