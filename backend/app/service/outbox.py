import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db.database import Database
from app.db.models import OutboxEvent
from app.domain.events import OutboxStatus, Topic
from app.infra.cbro import export_campaign
from app.infra.notifications import Notifier

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]

_MAX_RETRY_DELAY = timedelta(hours=1)
_ERROR_TEXT_MAX = 2000


def retry_delay(attempt: int) -> timedelta:
    """Exponential backoff: 2 s, 4 s, 8 s ... capped at one hour."""
    # Ограничиваем степень до расчёта: 2**attempt для больших attempt не помещается в timedelta.
    return min(timedelta(seconds=2 ** min(attempt, 12)), _MAX_RETRY_DELAY)


_REVIEW_TITLES = {"APPROVE": "одобрена", "DECLINE": "возвращена на доработку"}


def build_handlers(notifier: Notifier) -> dict[str, Handler]:
    async def user_registered(payload: dict[str, Any]) -> None:
        await notifier.send(f"Новый пользователь: {payload['email']}")

    async def sent_to_moderation(payload: dict[str, Any]) -> None:
        await notifier.send(
            f"Кампания «{payload['campaign_name']}» ({payload['campaign_id']}) ждёт модерации, "
            f"отправил {payload['actor']}"
        )

    async def reviewed(payload: dict[str, Any]) -> None:
        verdict = _REVIEW_TITLES[payload["action"]]
        comment = f": {payload['comment']}" if payload.get("comment") else ""
        await notifier.send(
            f"Кампания «{payload['campaign_name']}» {verdict} ({payload['actor']}){comment}"
        )

    async def activated(payload: dict[str, Any]) -> None:
        # Выгрузка в ЦБРО идемпотентна по id кампании: повтор доставки её не дублирует.
        export_campaign(payload["campaign_id"])
        await notifier.send(f"Кампания «{payload['campaign_name']}» запущена ({payload['actor']})")

    return {
        Topic.USER_REGISTERED: user_registered,
        Topic.CAMPAIGN_SENT_TO_MODERATION: sent_to_moderation,
        Topic.CAMPAIGN_REVIEWED: reviewed,
        Topic.CAMPAIGN_ACTIVATED: activated,
    }


class OutboxDispatcher:
    def __init__(
        self,
        db: Database,
        handlers: Mapping[str, Handler],
        *,
        batch_size: int,
        max_attempts: int,
    ) -> None:
        self._db = db
        self._handlers = handlers
        self._batch_size = batch_size
        self._max_attempts = max_attempts

    async def run_once(self) -> int:
        """Deliver one batch. Returns how many events were taken, so the caller can idle when 0."""
        now = datetime.now(UTC)
        async with self._db.unit_of_work() as uow:
            events = await uow.outbox.claim_batch(limit=self._batch_size, now=now)
            for event in events:
                await self._deliver(event, now)
        return len(events)

    async def _deliver(self, event: OutboxEvent, now: datetime) -> None:
        handler = self._handlers.get(event.topic)
        if handler is None:
            self._fail(event, now, f"no handler for topic {event.topic!r}", final=True)
            return

        event.attempts += 1
        try:
            await handler(event.payload)
        except Exception as exc:  # any handler failure is recorded and retried later
            self._fail(event, now, repr(exc), final=event.attempts >= self._max_attempts)
            return
        event.status = OutboxStatus.DONE
        event.processed_at = now

    def _fail(self, event: OutboxEvent, now: datetime, error: str, *, final: bool) -> None:
        event.last_error = error[:_ERROR_TEXT_MAX]
        if final:
            event.status = OutboxStatus.DEAD
            logger.error("outbox event %s (%s) is dead: %s", event.id, event.topic, error)
        else:
            event.available_at = now + retry_delay(event.attempts)
            logger.warning("outbox event %s (%s) failed: %s", event.id, event.topic, error)
