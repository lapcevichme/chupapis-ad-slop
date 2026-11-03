import asyncio
import os
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from app.bootstrap import build_chat_service
from app.core.config import BACKEND_DIR, Settings
from app.core.security.tokens import TokenCodec
from app.db.models import User
from app.db.seed import seed_demo_campaigns, seed_dictionaries
from app.domain.enums import Role
from app.infra.campaigns_api import CampaignsApi
from app.infra.checkpointer import setup_checkpointer
from app.main import create_app
from app.service.chat_sessions import SessionRegistry

# Тесты идут на настоящих Postgres, Redis и S3 из docker-compose.test.yml (порты не мешают рабочему стеку).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://adpilot:adpilot@localhost:5439/adpilot_test"
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6380/0")
TEST_STORAGE_ENDPOINT = os.environ.get("TEST_STORAGE_ENDPOINT", "http://localhost:9002")

_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = _PRIVATE.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
PUBLIC_PEM = (
    _PRIVATE.public_key()
    .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    .decode()
)

# Тесты, которые собирают Settings сами, тоже находят ключи.
os.environ.setdefault("JWT_PRIVATE_KEY", PRIVATE_PEM)
os.environ.setdefault("JWT_PUBLIC_KEY", PUBLIC_PEM)

MANAGER_ID = UUID(int=1)
MODERATOR_ID = UUID(int=2)
SESSION_ID = UUID(int=3)

_CODEC = TokenCodec(
    private_key=PRIVATE_PEM,
    public_key=PUBLIC_PEM,
    algorithm="RS256",
    access_ttl=timedelta(days=1),
    csrf_key=b"test",
)


def _bearer(user_id: UUID) -> dict[str, str]:
    token = _CODEC.issue_access(user_id=user_id, session_id=SESSION_ID, auth_version=1)
    return {"Authorization": f"Bearer {token}"}


# Токены выпущены на тестовых ключах и ссылаются на пользователей с фиксированными id,
# которых создаёт reset_database(): так тестам не нужен вход по паролю.
MANAGER = _bearer(MANAGER_ID)
MODERATOR = _bearer(MODERATOR_ID)

TABLES = (
    "outbox_events, auth_sessions, audit_log, chat_sessions, creatives, banners, contents, "
    "campaign_tags, campaign_places, campaign_segments, campaigns, studio_documents, "
    "media_objects, banner_type_channels, places, segments, segment_types, banner_types, "
    "channels, tags, topics, users"
)
CHECKPOINT_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")


def build_settings(**overrides) -> Settings:
    values = dict(
        _env_file=None,
        app_stage="test",
        database_url=TEST_DATABASE_URL,
        redis_url=TEST_REDIS_URL,
        storage_endpoint=TEST_STORAGE_ENDPOINT,
        storage_bucket="adpilot-test",
        jwt_private_key=PRIVATE_PEM,
        jwt_public_key=PUBLIC_PEM,
        rate_limit_enabled=False,
        llm_api_key="",
    )
    return Settings(**(values | overrides))


def alembic_config(database_url: str = TEST_DATABASE_URL) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(Path(BACKEND_DIR / "alembic")))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    """Схему создают настоящие миграции, так что тесты заодно проверяют, что они работают."""
    command.downgrade(alembic_config(), "base")
    command.upgrade(alembic_config(), "head")
    asyncio.run(setup_checkpointer(build_settings()))


ANONYMOUS = {"Authorization": ""}


class FakeMedia:
    """MediaSink без хранилища: запоминает, что сохранили, и отдаёт ссылку."""

    def __init__(self) -> None:
        self.saved: list[tuple[str, bytes]] = []

    async def save(self, data, *, kind, extension, content_type, owner_id=None) -> str:
        url = f"/api/media/{kind.value}-{len(self.saved)}.{extension}"
        self.saved.append((url, data))
        return url


def codes(response) -> list[str]:
    return [e["code"] for e in response.json()["errors"]]


async def initialize_database(app: FastAPI) -> None:
    """Чистая база: справочники, менеджер с модератором и демо-кампании из кейса."""
    async with app.state.db.unit_of_work() as uow:
        session = uow.session
        await session.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
        for table in CHECKPOINT_TABLES:
            await session.execute(text(f"TRUNCATE {table}"))
        users = {
            "ivanov.p": User(
                id=MANAGER_ID,
                email="ivanov.p@adpilot.local",
                username="ivanov.p",
                password_hash="x",
                role=Role.MANAGER,
            ),
            "petrova.m": User(
                id=MODERATOR_ID,
                email="petrova.m@adpilot.local",
                username="petrova.m",
                password_hash="x",
                role=Role.MODERATOR,
            ),
        }
        session.add_all(users.values())
        await session.flush()
        await seed_dictionaries(session, app.state.settings.seed_dir)
        await seed_demo_campaigns(session, app.state.settings.seed_dir, users)
    await app.state.redis.flushdb()


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(build_settings())
    with TestClient(app) as client:
        client.portal.call(initialize_database, app)
        # По умолчанию запросы идут от менеджера; роль и «без входа» тесты задают явно.
        client.headers.update(MANAGER)
        yield client


def install_chat(app: FastAPI, *, checkpointer=None, **models) -> None:
    """Собирает чат-сервис с подставленными моделями; агент ходит в API этого же приложения."""

    def api_factory(token: str) -> CampaignsApi:
        return CampaignsApi(token, base_url="http://api", transport=httpx.ASGITransport(app=app))

    app.state.chat = build_chat_service(
        checkpointer or app.state.checkpointer,
        app.state.settings,
        SessionRegistry(app.state.db),
        media=app.state.media_store,
        api_factory=api_factory,
        **models,
    )
