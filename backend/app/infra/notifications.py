import logging
from typing import Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    async def send(self, text: str) -> None: ...


class LogNotifier:
    async def send(self, text: str) -> None:
        logger.info("notification: %s", text)


class TelegramNotifier:
    def __init__(self, http: httpx.AsyncClient, *, bot_token: str, chat_id: str) -> None:
        self._http = http
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._chat_id = chat_id

    async def send(self, text: str) -> None:
        response = await self._http.post(
            self._url,
            json={"chat_id": self._chat_id, "text": text, "disable_web_page_preview": True},
        )
        # Raise so the outbox retries the event instead of silently dropping it.
        response.raise_for_status()


def build_notifier(settings: Settings, http: httpx.AsyncClient) -> Notifier:
    if settings.notifications_provider == "telegram":
        return TelegramNotifier(
            http,
            bot_token=settings.telegram_bot_token.get_secret_value(),
            chat_id=settings.telegram_chat_id,
        )
    return LogNotifier()
