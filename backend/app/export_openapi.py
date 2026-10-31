"""Выгружает OpenAPI в frontend/openapi.json: `uv run python -m app.export_openapi`.

Фронт генерирует типы из этого файла и собирается без запущенного бэкенда.
"""

import json

from app.core.config import BACKEND_DIR
from app.main import create_app

TARGET = BACKEND_DIR.parent / "frontend" / "openapi.json"

if __name__ == "__main__":
    TARGET.write_text(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI записан в {TARGET}")
