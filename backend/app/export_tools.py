"""Выгружает JSON-схемы инструментов агентов в docs/tools.json: `uv run python -m app.export_tools`.

Схемы генерируются из Pydantic-моделей, те же уходят модели в каждом запросе. Файл — артефакт §8 задания.
"""

import json

from app.core.config import BACKEND_DIR
from app.infra.agent.designer import DesignResult
from app.infra.agent.tools import tool_schemas

TARGET = BACKEND_DIR.parent / "docs" / "tools.json"


def export() -> dict:
    return {
        "chatAgent": tool_schemas(),
        "designAgent": [
            {
                "type": "function",
                "function": {
                    "name": "DesignResult",
                    "description": DesignResult.__doc__,
                    "parameters": DesignResult.model_json_schema(),
                },
            }
        ],
    }


if __name__ == "__main__":
    TARGET.write_text(json.dumps(export(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Схемы инструментов записаны в {TARGET}")
