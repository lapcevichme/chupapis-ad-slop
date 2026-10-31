import json
from typing import Any

from app.core.config import BACKEND_DIR
from app.infra.agent.designer import DesignEdit, DesignResult
from app.infra.agent.tools import tool_schemas

TARGET = BACKEND_DIR.parent / "docs" / "tools.json"


def export() -> dict[str, Any]:
    return {
        "chatAgent": tool_schemas(),
        "designAgent": [
            {
                "type": "function",
                "function": {
                    "name": model.__name__,
                    "description": model.__doc__,
                    "parameters": model.model_json_schema(),
                },
            }
            for model in (DesignResult, DesignEdit)
        ],
    }


if __name__ == "__main__":
    TARGET.write_text(json.dumps(export(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Схемы инструментов записаны в {TARGET}")
