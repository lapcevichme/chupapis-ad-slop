import os
import tempfile
from pathlib import Path

_db = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

MANAGER = {"X-User": "ivanov.p", "X-Role": "campaignManager"}
MODERATOR = {"X-User": "petrova.m", "X-Role": "campaignModerator"}


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)
    with TestClient(app) as c:
        yield c


def codes(response) -> list[str]:
    return [e["code"] for e in response.json()["errors"]]
