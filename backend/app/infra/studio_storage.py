import hashlib
import os
from pathlib import Path
from uuid import uuid4

from app.infra.media_storage import MediaStorage


class StudioStorage(MediaStorage):
    def save_document(self, document: str, png: bytes) -> tuple[str, str]:
        # Неизменяемая пара: повтор применения не размножает файлы и не портит прежние варианты.
        key = hashlib.sha256(document.encode() + png).hexdigest()[:32]
        name = f"upload-studio-{key}"
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self._atomic(self.media_dir / f"{name}.png", png)
        self._atomic(self.media_dir / f"{name}.json", document.encode())
        return key, f"{self.media_base_url}/{name}.png"

    def read_document(self, key: str) -> str | None:
        path = self.media_dir / f"upload-studio-{key}.json"
        return path.read_text() if path.is_file() else None

    def contains(self, document: str, png: bytes) -> bool:
        key = hashlib.sha256(document.encode() + png).hexdigest()[:32]
        return (self.media_dir / f"upload-studio-{key}.json").is_file()

    @staticmethod
    def _atomic(path: Path, data: bytes) -> None:
        if path.exists():
            return
        temp = path.with_suffix(f".{uuid4().hex}.tmp")
        try:
            temp.write_bytes(data)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
