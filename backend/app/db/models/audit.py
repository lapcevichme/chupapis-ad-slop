from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, pg_enum, utcnow
from app.db.models.users import User
from app.domain.enums import AuditAction, AuditEntity


class AuditEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    # Без внешнего ключа: журнал переживает удаление кампании.
    campaign_id: Mapped[int | None] = mapped_column(Integer)
    entity: Mapped[AuditEntity] = mapped_column(pg_enum(AuditEntity, "audit_entity"))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[AuditAction] = mapped_column(pg_enum(AuditAction, "audit_action"))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (Index("ix_audit_log_campaign_at", "campaign_id", "at", "id"),)
