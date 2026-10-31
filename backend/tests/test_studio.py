import asyncio
import json
import struct
import zlib

import pytest

from app.contracts.studio import StudioGenerationBody
from app.infra.agent.studio_designer import StudioDesigner
from tests.conftest import MANAGER, MODERATOR, codes
from tests.test_agent import ScriptedModel, call, tool_message

DOCUMENT = {
    "name": "Тестовый макет",
    "format": "STORY",
    "width": 300,
    "height": 600,
    "background": "#3155ff",
    "layers": [
        {
            "id": "title",
            "name": "Оффер",
            "kind": "text",
            "role": "title",
            "text": "Вклад 16%",
            "x": 20,
            "y": 20,
            "width": 260,
            "height": 100,
        }
    ],
}


def png(width=600, height=1200):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\0" * width * 4) * height))
        + chunk(b"IEND", b"")
    )


def save(client, document=DOCUMENT, data=None, headers=MANAGER):
    return client.post(
        "/studio/documents",
        headers=headers,
        data={"document": json.dumps(document)},
        files={"file": ("../../design.png", png() if data is None else data, "image/png")},
    )


def test_scene_survives_reload_without_changing_campaign(client):
    before = client.get("/campaigns/101", headers=MANAGER).json()
    response = save(client)
    assert response.status_code == 201
    stored = response.json()
    fetched = client.get(f"/studio/documents/{stored['id']}", headers=MODERATOR)
    assert fetched.status_code == 200 and fetched.json() == stored["document"]
    assert client.get("/campaigns/101", headers=MANAGER).json() == before
    assert ".." not in stored["url"]


def test_save_retry_is_content_addressed_and_does_not_use_quota_twice(client):
    first = save(client).json()
    settings = client.app.state.settings
    used = sum(p.stat().st_size for p in settings.media_dir.glob("upload-*"))
    settings.media_upload_max_total_bytes = used
    second = save(client)
    assert second.status_code == 201 and first == second.json()
    assert len(list(settings.media_dir.glob("upload-studio-*"))) == 2


def test_moderator_cannot_save_or_generate(client):
    assert codes(save(client, headers=MODERATOR)) == ["ROLE_FORBIDDEN"]
    result = client.post(
        "/studio/generate", headers=MODERATOR, json={"document": DOCUMENT, "prompt": "Ярче"}
    )
    assert codes(result) == ["ROLE_FORBIDDEN"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["layers"][0].update(text="А" * 101),
        lambda d: d["layers"].append(d["layers"][0]),
        lambda d: d["layers"][0].update(kind="image", src="javascript:alert(1)"),
    ],
)
def test_invalid_copy_or_layer_is_rejected(client, mutate):
    document = json.loads(json.dumps(DOCUMENT))
    mutate(document)
    assert codes(save(client, document=document)) == ["STUDIO_DOCUMENT_INVALID"]


def test_render_dimensions_and_format_are_checked(client):
    assert codes(save(client, data=png(300, 600))) == ["STUDIO_RENDER_INVALID"]
    assert codes(save(client, data=b"<svg></svg>")) == ["IMAGE_FORMAT_UNSUPPORTED"]


def test_generation_without_key_is_an_explicit_error(client):
    result = client.post(
        "/studio/generate", headers=MANAGER, json={"document": DOCUMENT, "prompt": "Ярче"}
    )
    assert codes(result) == ["STUDIO_AI_UNAVAILABLE"]


def test_ai_may_relayout_but_cannot_invent_offer_copy():
    changed = json.loads(json.dumps(DOCUMENT))
    changed["layers"][0]["text"] = "Вклад 99%"
    generator = StudioDesigner(
        ScriptedModel(
            script=[
                tool_message(
                    call(
                        "StudioGenerationResult",
                        {"variants": [changed]},
                        1,
                    )
                )
            ]
        )
    )
    with pytest.raises(Exception, match="несовместимый"):
        asyncio.run(generator.generate(StudioGenerationBody(document=DOCUMENT, prompt="Ярче")))
