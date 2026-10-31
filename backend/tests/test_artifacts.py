"""Артефакты §8 не расходятся с кодом."""

import json

from app.export_tools import TARGET, export


def test_tools_json_is_up_to_date():
    # Если упало: uv run python -m app.export_tools
    assert json.loads(TARGET.read_text(encoding="utf-8")) == json.loads(json.dumps(export(), ensure_ascii=False))
