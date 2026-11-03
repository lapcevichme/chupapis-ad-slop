import hashlib
import struct
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.contracts.studio import (
    StoredStudioDocument,
    StudioDocument,
    StudioGenerationBody,
    StudioGenerationResult,
)
from app.core.errors import fail, not_found
from app.db.database import Database
from app.db.models import MediaObject
from app.db.models import StudioDocument as StudioDocumentRow
from app.db.uow import UnitOfWork
from app.domain.media import MediaKind
from app.domain.users import CurrentUser, Permission, ensure_can
from app.infra.storage import ObjectStorage

SIGNATURES = {b"\xff\xd8\xff": ("jpg", "image/jpeg"), b"\x89PNG\r\n\x1a\n": ("png", "image/png")}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Квота считается по файлам, которые загрузил человек; то, что нагенерировал агент, в неё не входит.
QUOTA_KINDS = (MediaKind.UPLOAD, MediaKind.STUDIO)


class MediaStore:
    """Кладёт файл в S3 и записывает его в media_objects. Работает со своей транзакцией, поэтому годится
    и для запроса, и для агента, который пишет посреди графа, вне транзакции кампании."""

    def __init__(self, db: Database, storage: ObjectStorage, *, media_base_url: str) -> None:
        self._db = db
        self._storage = storage
        self.media_base_url = media_base_url.rstrip("/")

    def url(self, key: str) -> str:
        return f"{self.media_base_url}/{key}"

    async def save(
        self,
        data: bytes,
        *,
        kind: MediaKind,
        extension: str,
        content_type: str,
        owner_id: UUID | None = None,
    ) -> str:
        # Имя задаём сами: имя файла от клиента не должно попасть в ключ.
        key = f"{kind.value}-{uuid4().hex}.{extension}"
        await self._storage.put(key, data, content_type=content_type)
        async with self._db.unit_of_work() as uow:
            await self.register(
                uow, key, data, kind=kind, content_type=content_type, owner_id=owner_id
            )
        return self.url(key)

    async def register(
        self,
        uow: UnitOfWork,
        key: str,
        data: bytes,
        *,
        kind: MediaKind,
        content_type: str,
        owner_id: UUID | None,
    ) -> MediaObject:
        row = MediaObject(
            key=key, kind=kind, content_type=content_type, size_bytes=len(data), owner_id=owner_id
        )
        uow.session.add(row)
        await uow.flush()
        return row

    async def uploads_size(self, uow: UnitOfWork) -> int:
        total = await uow.session.scalar(
            select(func.coalesce(func.sum(MediaObject.size_bytes), 0)).where(
                MediaObject.kind.in_(QUOTA_KINDS)
            )
        )
        return int(total or 0)


class MediaService:
    def __init__(
        self,
        uow: UnitOfWork,
        store: MediaStore,
        storage: ObjectStorage,
        *,
        max_bytes: int,
        max_total_bytes: int,
    ) -> None:
        self._uow = uow
        self._store = store
        self._storage = storage
        self.max_bytes = max_bytes
        self.max_total_bytes = max_total_bytes

    async def upload_image(self, data: bytes, user: CurrentUser) -> str:
        ensure_can(user, Permission.MEDIA_WRITE)
        if not data:
            raise fail("IMAGE_EMPTY", "file")
        if len(data) > self.max_bytes:
            raise fail("IMAGE_TOO_LARGE", "file")
        # Смотрим на сами байты: тип и имя файла присылает клиент, а SVG из браузера может выполнить скрипт.
        found = next((v for sign, v in SIGNATURES.items() if data.startswith(sign)), None)
        if found is None:
            raise fail("IMAGE_FORMAT_UNSUPPORTED", "file")
        extension, content_type = found
        if await self._store.uploads_size(self._uow) + len(data) > self.max_total_bytes:
            raise fail("MEDIA_STORAGE_FULL", "file")
        key = f"{MediaKind.UPLOAD.value}-{uuid4().hex}.{extension}"
        await self._storage.put(key, data, content_type=content_type)
        await self._store.register(
            self._uow, key, data, kind=MediaKind.UPLOAD, content_type=content_type, owner_id=user.id
        )
        return self._store.url(key)

    async def read(self, key: str) -> tuple[bytes, str]:
        row = await self._uow.session.scalar(select(MediaObject).where(MediaObject.key == key))
        stored = await self._storage.get(key) if row is not None else None
        if stored is None:
            raise not_found("media", key)
        return stored.data, row.content_type if row else stored.content_type


class StudioGenerator(Protocol):
    async def generate(self, body: StudioGenerationBody) -> StudioGenerationResult: ...


class StudioService:
    def __init__(
        self,
        uow: UnitOfWork,
        store: MediaStore,
        storage: ObjectStorage,
        *,
        max_bytes: int,
        max_total_bytes: int,
        generator: StudioGenerator | None = None,
    ) -> None:
        self._uow = uow
        self._store = store
        self._storage = storage
        self.max_bytes = max_bytes
        self.max_total_bytes = max_total_bytes
        self.generator = generator

    async def save(
        self, document: StudioDocument, png: bytes, user: CurrentUser
    ) -> StoredStudioDocument:
        ensure_can(user, Permission.MEDIA_WRITE)
        if len(png) > self.max_bytes:
            raise fail("IMAGE_TOO_LARGE", "file")
        if len(png) < 33 or png[:8] != PNG_SIGNATURE or png[12:16] != b"IHDR":
            raise fail("IMAGE_FORMAT_UNSUPPORTED", "file")
        if struct.unpack(">II", png[16:24]) != (document.width * 2, document.height * 2):
            raise fail(
                "STUDIO_RENDER_INVALID", "file", "Размер PNG не совпадает с макетом в масштабе 2×"
            )
        encoded = document.model_dump_json()
        # Неизменяемая пара: повтор применения не размножает файлы и не портит прежние варианты.
        key = hashlib.sha256(encoded.encode() + png).hexdigest()[:32]
        existing = await self._uow.session.get(StudioDocumentRow, key)
        if existing is None:
            if await self._store.uploads_size(self._uow) + len(png) > self.max_total_bytes:
                raise fail("MEDIA_STORAGE_FULL", "file")
            name = f"{MediaKind.STUDIO.value}-{key}.png"
            await self._storage.put(name, png, content_type="image/png")
            render = await self._store.register(
                self._uow,
                name,
                png,
                kind=MediaKind.STUDIO,
                content_type="image/png",
                owner_id=user.id,
            )
            self._uow.session.add(
                StudioDocumentRow(
                    id=key,
                    document=document.model_dump(mode="json"),
                    render_id=render.id,
                    owner_id=user.id,
                )
            )
            await self._uow.flush()
            url = self._store.url(name)
        else:
            render_row = await self._uow.session.get(MediaObject, existing.render_id)
            assert render_row is not None
            url = self._store.url(render_row.key)
        return StoredStudioDocument(id=key, url=url, document=document)

    async def get(self, key: str) -> StudioDocument:
        row = await self._uow.session.get(StudioDocumentRow, key)
        if row is None:
            raise not_found("studioDocument", key)
        return StudioDocument.model_validate(row.document)

    async def generate(
        self, body: StudioGenerationBody, user: CurrentUser
    ) -> StudioGenerationResult:
        ensure_can(user, Permission.MEDIA_WRITE)
        if self.generator is None:
            raise fail(
                "STUDIO_AI_UNAVAILABLE",
                message="AI-дизайнер не настроен. Доступны ручные правки и локальные макеты.",
            )
        return await self.generator.generate(body)
