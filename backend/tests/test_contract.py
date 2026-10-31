import json
from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def test_openapi_matches_frontend_contract():
    path = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
    assert create_app(Settings(_env_file=None)).openapi() == json.loads(path.read_text())
