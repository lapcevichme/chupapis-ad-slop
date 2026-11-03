from typing import Protocol
from uuid import UUID

from app.domain.media import MediaKind


class MediaSink(Protocol):
    """Куда агент кладёт то, что нагенерировал. Возвращает ссылку, которую можно вставить в JSON баннера."""

    async def save(
        self,
        data: bytes,
        *,
        kind: MediaKind,
        extension: str,
        content_type: str,
        owner_id: UUID | None = None,
    ) -> str: ...
