from pathlib import Path
from uuid import uuid4

UPLOAD_PREFIX = "upload-"


class MediaStorage:
    def __init__(self, media_dir: Path, media_base_url: str) -> None:
        self.media_dir = media_dir
        self.media_base_url = media_base_url.rstrip("/")

    def uploads_size(self) -> int:
        if not self.media_dir.exists():
            return 0
        return sum(path.stat().st_size for path in self.media_dir.glob(f"{UPLOAD_PREFIX}*"))

    def save_upload(self, data: bytes, extension: str) -> str:
        # Имя задаём сами: имя файла от клиента не должно попасть в путь.
        name = f"{UPLOAD_PREFIX}{uuid4().hex}.{extension}"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        (self.media_dir / name).write_bytes(data)
        return f"{self.media_base_url}/{name}"
