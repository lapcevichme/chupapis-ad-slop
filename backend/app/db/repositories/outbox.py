from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent
from app.domain.events import OutboxStatus, Topic


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, topic: Topic, payload: dict[str, Any]) -> None:
        self._session.add(OutboxEvent(topic=topic.value, payload=payload))

    async def claim_batch(self, *, limit: int, now: datetime) -> Sequence[OutboxEvent]:
        # SKIP LOCKED lets several workers run side by side without taking the same event.
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.PENDING, OutboxEvent.available_at <= now)
            .order_by(OutboxEvent.available_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self._session.scalars(stmt)).all()
