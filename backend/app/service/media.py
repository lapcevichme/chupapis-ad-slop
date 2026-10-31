import asyncio

from app.core.errors import fail
from app.domain.actors import Actor, require_role
from app.domain.enums import Role
from app.infra.media_storage import MediaStorage

SIGNATURES = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png"}


class MediaService:
    def __init__(self, storage: MediaStorage, *, max_bytes: int, max_total_bytes: int) -> None:
        self.storage = storage
        self.max_bytes = max_bytes
        self.max_total_bytes = max_total_bytes

    async def upload_image(self, data: bytes, actor: Actor) -> str:
        require_role(actor, Role.MANAGER)
        if not data:
            raise fail("IMAGE_EMPTY", "file")
        if len(data) > self.max_bytes:
            raise fail("IMAGE_TOO_LARGE", "file")
        # Смотрим на сами байты: тип и имя файла присылает клиент, а SVG из браузера может выполнить скрипт.
        extension = next((ext for sign, ext in SIGNATURES.items() if data.startswith(sign)), None)
        if extension is None:
            raise fail("IMAGE_FORMAT_UNSUPPORTED", "file")
        used = await asyncio.to_thread(self.storage.uploads_size)
        if used + len(data) > self.max_total_bytes:
            raise fail("MEDIA_STORAGE_FULL", "file")
        return await asyncio.to_thread(self.storage.save_upload, data, extension)
