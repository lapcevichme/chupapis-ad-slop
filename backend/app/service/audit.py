from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEntry
from app.domain.audit import diff as diff
from app.domain.enums import AuditAction, AuditEntity


def record(
    session: AsyncSession,
    *,
    campaign_id: int | None,
    entity: AuditEntity,
    entity_id: int,
    action: AuditAction,
    actor_id: UUID,
    changes: dict[str, Any] | None = None,
    comment: str | None = None,
) -> None:
    session.add(
        AuditEntry(
            campaign_id=campaign_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            changes=changes or None,
            actor_id=actor_id,
            comment=comment,
        )
    )
