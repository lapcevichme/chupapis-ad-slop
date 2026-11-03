from datetime import datetime
from typing import Any

from sqlalchemy import Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UuidPkMixin, pg_enum, utcnow
from app.domain.events import OutboxStatus


class OutboxEvent(UuidPkMixin, Base):
    """Побочный эффект, записанный в той же транзакции, что и вызвавшее его изменение.
    Воркер доставляет его после коммита, с повторами; обработчики идемпотентны."""

    __tablename__ = "outbox_events"

    topic: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[OutboxStatus] = mapped_column(
        pg_enum(OutboxStatus, "outbox_status"),
        default=OutboxStatus.PENDING,
        server_default=OutboxStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    available_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    processed_at: Mapped[datetime | None]

    __table_args__ = (
        Index(
            "ix_outbox_events_pending", "available_at", postgresql_where=text("status = 'pending'")
        ),
    )
