"""Диктовка: запрос к OpenRouter, повтор при сбое и ошибки HTTP-ручки."""

import asyncio
import base64
import json

import httpx
import pytest

from app.core.config import Settings
from app.infra import speech as infra
from app.infra.speech import OpenRouterTranscriber, TranscriptionFailed
from app.service.speech import SpeechService
from tests.conftest import MANAGER, codes


class FakeTranscriber:
    def __init__(self, result: str | Exception = "привет"):
        self.result = result
        self.calls: list[tuple[bytes, str]] = []

    async def transcribe(self, audio: bytes, audio_format: str) -> str:
        self.calls.append((audio, audio_format))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def transcriber(responses: list, monkeypatch):
    monkeypatch.setattr(infra, "TRANSCRIBE_RETRY_DELAY", 0)
    calls = []

    def handler(request):
        calls.append(request)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    settings = Settings(_env_file=None, llm_api_key="key", stt_model="test/stt")
    return OpenRouterTranscriber(settings, transport=httpx.MockTransport(handler)), calls


def test_sends_base64_audio_with_model_and_language(monkeypatch):
    stt, calls = transcriber([httpx.Response(200, json={"text": " привет "})], monkeypatch)
    assert asyncio.run(stt.transcribe(b"audio", "webm")) == "привет"
    assert str(calls[0].url).endswith("/audio/transcriptions")
    assert calls[0].headers["Authorization"] == "Bearer key"
    assert json.loads(calls[0].content) == {
        "model": "test/stt",
        "input_audio": {"data": base64.b64encode(b"audio").decode(), "format": "webm"},
        "language": "ru",
    }


def test_retries_transient_failure_once(monkeypatch):
    stt, calls = transcriber(
        [httpx.Response(503), httpx.Response(200, json={"text": "да"})], monkeypatch
    )
    assert asyncio.run(stt.transcribe(b"audio", "webm")) == "да"
    assert len(calls) == 2


def test_gives_up_after_second_failure(monkeypatch):
    stt, calls = transcriber([httpx.ReadError("reset"), httpx.Response(429)], monkeypatch)
    with pytest.raises(TranscriptionFailed):
        asyncio.run(stt.transcribe(b"audio", "webm"))
    assert len(calls) == 2


def test_client_error_is_not_retried(monkeypatch):
    stt, calls = transcriber([httpx.Response(400)], monkeypatch)
    with pytest.raises(TranscriptionFailed):
        asyncio.run(stt.transcribe(b"audio", "webm"))
    assert len(calls) == 1


def test_response_without_text_is_failure(monkeypatch):
    stt, _ = transcriber([httpx.Response(200, json={"usage": {}})], monkeypatch)
    with pytest.raises(TranscriptionFailed):
        asyncio.run(stt.transcribe(b"audio", "webm"))


def post(client, data=b"audio", content_type="audio/webm;codecs=opus", headers=MANAGER):
    return client.post(
        "/speech/transcriptions",
        headers=headers,
        files={"file": ("speech", data, content_type)},
    )


def use(client, fake: FakeTranscriber, max_audio_bytes: int = 100) -> None:
    client.app.state.speech = SpeechService(fake, max_audio_bytes=max_audio_bytes)


def test_endpoint_returns_text_and_maps_browser_format(client):
    fake = FakeTranscriber()
    use(client, fake)
    response = post(client)
    assert response.status_code == 200
    assert response.json() == {"text": "привет"}
    assert fake.calls == [(b"audio", "webm")]


def test_safari_recording_is_sent_as_m4a(client):
    fake = FakeTranscriber()
    use(client, fake)
    assert post(client, content_type="audio/mp4").status_code == 200
    assert fake.calls[0][1] == "m4a"


def test_endpoint_requires_user(client):
    use(client, FakeTranscriber())
    assert codes(post(client, headers={})) == ["USER_REQUIRED"]


@pytest.mark.parametrize(
    ("data", "content_type", "code"),
    [
        (b"", "audio/webm", "AUDIO_EMPTY"),
        (b"x" * 101, "audio/webm", "AUDIO_TOO_LARGE"),
        (b"audio", "text/plain", "AUDIO_FORMAT_UNSUPPORTED"),
    ],
)
def test_bad_audio_never_reaches_provider(client, data, content_type, code):
    fake = FakeTranscriber()
    use(client, fake)
    response = post(client, data, content_type)
    assert response.status_code == 400
    assert codes(response) == [code]
    assert fake.calls == []


def test_provider_failure_is_502(client):
    use(client, FakeTranscriber(TranscriptionFailed("HTTP 500")))
    response = post(client)
    assert response.status_code == 502
    assert codes(response) == ["TRANSCRIPTION_FAILED"]


def test_without_key_endpoint_reports_unavailable(client):
    response = post(client)
    assert response.status_code == 503
    assert codes(response) == ["TRANSCRIPTION_UNAVAILABLE"]
