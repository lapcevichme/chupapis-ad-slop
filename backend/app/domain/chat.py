from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class StreamEvent:
    event: str
    data: dict[str, Any] = field(default_factory=dict)
