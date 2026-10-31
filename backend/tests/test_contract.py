import json
from pathlib import Path

from app.main import app


def test_openapi_matches_frontend_contract():
    path = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"
    assert app.openapi() == json.loads(path.read_text())
