from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class StreamEvent:
    event: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChatSummary:
    session_id: str
    campaign_id: int | None
    name: str
    created_at: datetime
    archived_at: datetime | None
