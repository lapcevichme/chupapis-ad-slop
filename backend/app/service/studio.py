import asyncio
import struct
from typing import Protocol

from app.contracts.studio import (
    StoredStudioDocument,
    StudioDocument,
    StudioGenerationBody,
    StudioGenerationResult,
)
from app.core.errors import fail, not_found
from app.domain.actors import Actor, require_role
from app.domain.enums import Role
from app.infra.studio_storage import StudioStorage


class StudioGenerator(Protocol):
    async def generate(self, body: StudioGenerationBody) -> StudioGenerationResult: ...


class StudioService:
    def __init__(
        self,
        storage: StudioStorage,
        *,
        max_bytes: int,
        max_total_bytes: int,
        generator: StudioGenerator | None = None,
    ) -> None:
        self.storage = storage
        self.max_bytes = max_bytes
        self.max_total_bytes = max_total_bytes
        self.generator = generator

    async def save(
        self, document: StudioDocument, png: bytes, actor: Actor
    ) -> StoredStudioDocument:
        require_role(actor, Role.MANAGER)
        if len(png) > self.max_bytes:
            raise fail("IMAGE_TOO_LARGE", "file")
        if len(png) < 33 or png[:8] != b"\x89PNG\r\n\x1a\n" or png[12:16] != b"IHDR":
            raise fail("IMAGE_FORMAT_UNSUPPORTED", "file")
        if struct.unpack(">II", png[16:24]) != (document.width * 2, document.height * 2):
            raise fail(
                "STUDIO_RENDER_INVALID", "file", "Размер PNG не совпадает с макетом в масштабе 2×"
            )
        encoded = document.model_dump_json()
        exists = await asyncio.to_thread(self.storage.contains, encoded, png)
        used = await asyncio.to_thread(self.storage.uploads_size)
        if not exists and used + len(png) + len(encoded.encode()) > self.max_total_bytes:
            raise fail("MEDIA_STORAGE_FULL", "file")
        key, url = await asyncio.to_thread(self.storage.save_document, encoded, png)
        return StoredStudioDocument(id=key, url=url, document=document)

    async def get(self, key: str) -> StudioDocument:
        raw = await asyncio.to_thread(self.storage.read_document, key)
        if raw is None:
            raise not_found("studioDocument", key)
        return StudioDocument.model_validate_json(raw)

    async def generate(self, body: StudioGenerationBody, actor: Actor) -> StudioGenerationResult:
        require_role(actor, Role.MANAGER)
        if self.generator is None:
            raise fail(
                "STUDIO_AI_UNAVAILABLE",
                message="AI-дизайнер не настроен. Доступны ручные правки и локальные макеты.",
            )
        return await self.generator.generate(body)
