from datetime import UTC, datetime
from typing import Any


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
