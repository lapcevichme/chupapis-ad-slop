"""Загрузка фото менеджером: роль, формат, лимиты и раздача файла."""

import pytest

from tests.conftest import MANAGER, MODERATOR, codes

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def upload(client, data: bytes, headers=MANAGER, name="photo.jpg", content_type="image/jpeg"):
    return client.post("/media/images", files={"file": (name, data, content_type)}, headers=headers)


@pytest.fixture
def media_settings(client, tmp_path):
    settings = client.app.state.settings
    previous = (
        settings.media_dir,
        settings.media_upload_max_bytes,
        settings.media_upload_max_total_bytes,
    )
    # В tmp_path уже лежит база клиента, а здесь считаем только загрузки.
    settings.media_dir = tmp_path / "uploads"
    settings.media_dir.mkdir()
    yield settings
    settings.media_dir, settings.media_upload_max_bytes, settings.media_upload_max_total_bytes = (
        previous
    )


@pytest.mark.parametrize(("data", "extension"), [(JPEG, "jpg"), (PNG, "png")])
def test_manager_uploads_image(client, media_settings, data, extension):
    response = upload(client, data)

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("/api/media/upload-") and url.endswith(f".{extension}")
    assert (media_settings.media_dir / url.rsplit("/", 1)[1]).read_bytes() == data


def test_format_comes_from_bytes_not_from_client(client, media_settings):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    response = upload(client, svg, name="photo.jpg", content_type="image/jpeg")

    assert response.status_code == 400 and codes(response) == ["IMAGE_FORMAT_UNSUPPORTED"]
    assert list(media_settings.media_dir.iterdir()) == []


def test_client_file_name_does_not_reach_path(client, media_settings):
    response = upload(client, JPEG, name="../../evil.jpg")

    assert response.status_code == 201
    assert "evil" not in response.json()["url"]
    assert len(list(media_settings.media_dir.iterdir())) == 1


def test_empty_file_is_rejected(client, media_settings):
    assert codes(upload(client, b"")) == ["IMAGE_EMPTY"]


def test_file_size_limit(client, media_settings):
    media_settings.media_upload_max_bytes = 50

    response = upload(client, JPEG)

    assert response.status_code == 400 and codes(response) == ["IMAGE_TOO_LARGE"]
    assert list(media_settings.media_dir.iterdir()) == []


def test_total_uploads_limit(client, media_settings):
    media_settings.media_upload_max_total_bytes = 150
    assert upload(client, JPEG).status_code == 201

    response = upload(client, JPEG)

    assert response.status_code == 400 and codes(response) == ["MEDIA_STORAGE_FULL"]


def test_only_manager_can_upload(client, media_settings):
    assert codes(upload(client, JPEG, headers=MODERATOR)) == ["ROLE_FORBIDDEN"]
    assert (
        client.post("/media/images", files={"file": ("a.jpg", JPEG, "image/jpeg")}).status_code
        == 400
    )
    assert list(media_settings.media_dir.iterdir()) == []
