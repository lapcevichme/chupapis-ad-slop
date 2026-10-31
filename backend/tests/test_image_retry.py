"""Генерация картинки повторяется при сбоях и сдаётся только после 4 попыток."""

import asyncio
import base64

import httpx
import pytest

from app.agent import llm
from app.core.config import Settings

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 16).decode()


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    monkeypatch.setattr(llm, "IMAGE_RETRY_DELAYS", (0, 0, 0))


def generator(responses: list, tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return llm.OpenRouterImageGenerator("test/model", Settings(_env_file=None, media_dir=tmp_path), transport=httpx.MockTransport(handler)), calls


def test_retries_until_success(tmp_path):
    gen, calls = generator(
        [
            httpx.ReadError("connection reset"),
            httpx.Response(502),
            httpx.Response(429),
            httpx.Response(200, json={"data": [{"b64_json": PNG}]}),
        ], tmp_path
    )
    url = asyncio.run(gen.generate("coins", "1024x1536"))
    assert url.endswith(".png") and len(calls) == 4


def test_gives_up_after_four_attempts(tmp_path):
    gen, calls = generator([httpx.Response(503)] * 4, tmp_path)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(gen.generate("coins"))
    assert len(calls) == 4


def test_client_error_is_not_retried(tmp_path):
    gen, calls = generator([httpx.Response(400, json={"error": "bad prompt"})], tmp_path)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(gen.generate("coins"))
    assert len(calls) == 1
