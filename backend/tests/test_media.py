"""Загрузка фото менеджером: роль, формат, лимиты и раздача файла."""

import pytest
from sqlalchemy import func, select

from app.db.models import MediaObject
from tests.conftest import ANONYMOUS, MANAGER, MODERATOR, codes

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def upload(client, data: bytes, headers=MANAGER, name="photo.jpg", content_type="image/jpeg"):
    return client.post("/media/images", files={"file": (name, data, content_type)}, headers=headers)


def stored_rows(client) -> int:
    async def count(app):
        async with app.state.db.unit_of_work() as uow:
            return await uow.session.scalar(select(func.count()).select_from(MediaObject))

    return client.portal.call(count, client.app)


@pytest.fixture
def limits(client):
    settings = client.app.state.settings
    previous = (settings.media_upload_max_bytes, settings.media_upload_max_total_bytes)
    yield settings
    settings.media_upload_max_bytes, settings.media_upload_max_total_bytes = previous


@pytest.mark.parametrize(
    ("data", "extension", "content_type"),
    [(JPEG, "jpg", "image/jpeg"), (PNG, "png", "image/png")],
)
def test_manager_uploads_image_and_it_is_served_back(client, data, extension, content_type):
    response = upload(client, data)

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("/api/media/upload-") and url.endswith(f".{extension}")
    # Прокси фронтенда снимает /api, поэтому бэкенд видит путь без него.
    served = client.get(url.removeprefix("/api"), headers=ANONYMOUS)
    assert served.status_code == 200 and served.content == data
    assert served.headers["content-type"] == content_type
    assert "immutable" in served.headers["cache-control"]


def test_unknown_file_is_not_found(client):
    assert client.get("/media/upload-nope.png", headers=ANONYMOUS).status_code == 404


def test_format_comes_from_bytes_not_from_client(client, limits):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    response = upload(client, svg, name="photo.jpg", content_type="image/jpeg")

    assert response.status_code == 400 and codes(response) == ["IMAGE_FORMAT_UNSUPPORTED"]
    assert stored_rows(client) == 0


def test_client_file_name_does_not_reach_the_key(client):
    response = upload(client, JPEG, name="../../evil.jpg")

    assert response.status_code == 201
    assert "evil" not in response.json()["url"]
    assert stored_rows(client) == 1


def test_empty_file_is_rejected(client):
    assert codes(upload(client, b"")) == ["IMAGE_EMPTY"]


def test_file_size_limit(client, limits):
    limits.media_upload_max_bytes = 50

    response = upload(client, JPEG)

    assert response.status_code == 400 and codes(response) == ["IMAGE_TOO_LARGE"]
    assert stored_rows(client) == 0


def test_total_uploads_limit(client, limits):
    limits.media_upload_max_total_bytes = 150
    assert upload(client, JPEG).status_code == 201

    response = upload(client, JPEG)

    assert response.status_code == 400 and codes(response) == ["MEDIA_STORAGE_FULL"]


def test_only_manager_can_upload(client):
    assert codes(upload(client, JPEG, headers=MODERATOR)) == ["ROLE_FORBIDDEN"]
    assert upload(client, JPEG, headers=ANONYMOUS).status_code == 401
    assert stored_rows(client) == 0
