from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEntry
from app.domain.audit import diff as diff
from app.domain.audit import utcnow
from app.domain.enums import AuditAction, AuditEntity


def record(
    session: AsyncSession,
    *,
    campaign_id: int | None,
    entity: AuditEntity,
    entity_id: int,
    action: AuditAction,
    actor: str,
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
            at=utcnow(),
            actor=actor,
            comment=comment,
        )
    )
