from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domain.enums import AuditAction, AuditEntity
from app.models import AuditEntry


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict) and value:
        result: dict[str, Any] = {}
        for key, item in value.items():
            result |= _flatten(item, f"{prefix}.{key}" if prefix else key)
        return result
    return {prefix: value}


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """{поле: {from, to}} по изменённым полям; вложенные объекты разворачиваются в пути через точку."""
    old, new = _flatten(before), _flatten(after)
    return {
        key: {"from": old.get(key), "to": new.get(key)}
        for key in sorted(old.keys() | new.keys())
        if old.get(key) != new.get(key)
    }


def record(
    session: Session,
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
