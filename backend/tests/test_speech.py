"""Диктовка: запрос к OpenRouter, повтор при сбое и ошибки HTTP-ручки."""

import asyncio
import base64
import json

import httpx
import pytest

from app.core.config import Settings
from app.infra import speech as infra
from app.infra.speech import OpenRouterSynthesizer, OpenRouterTranscriber, SpeechFailed
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
    monkeypatch.setattr(infra, "SPEECH_RETRY_DELAY", 0)
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
    with pytest.raises(SpeechFailed):
        asyncio.run(stt.transcribe(b"audio", "webm"))
    assert len(calls) == 2


def test_client_error_is_not_retried(monkeypatch):
    stt, calls = transcriber([httpx.Response(400)], monkeypatch)
    with pytest.raises(SpeechFailed):
        asyncio.run(stt.transcribe(b"audio", "webm"))
    assert len(calls) == 1


def test_response_without_text_is_failure(monkeypatch):
    stt, _ = transcriber([httpx.Response(200, json={"usage": {}})], monkeypatch)
    with pytest.raises(SpeechFailed):
        asyncio.run(stt.transcribe(b"audio", "webm"))


def post(client, data=b"audio", content_type="audio/webm;codecs=opus", headers=MANAGER):
    return client.post(
        "/speech/transcriptions",
        headers=headers,
        files={"file": ("speech", data, content_type)},
    )


def use(client, fake: FakeTranscriber, max_audio_bytes: int = 100) -> None:
    client.app.state.speech = SpeechService(
        fake, None, max_audio_bytes=max_audio_bytes, max_text_chars=10
    )


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
    use(client, FakeTranscriber(SpeechFailed("HTTP 500")))
    response = post(client)
    assert response.status_code == 502
    assert codes(response) == ["TRANSCRIPTION_FAILED"]


def test_without_key_endpoint_reports_unavailable(client):
    response = post(client)
    assert response.status_code == 503
    assert codes(response) == ["TRANSCRIPTION_UNAVAILABLE"]


class FakeSynthesizer:
    def __init__(self, result: bytes | Exception = b"mp3"):
        self.result = result
        self.calls: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.calls.append(text)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def synthesizer(responses: list, monkeypatch):
    monkeypatch.setattr(infra, "SPEECH_RETRY_DELAY", 0)
    calls = []

    def handler(request):
        calls.append(request)
        return responses.pop(0)

    settings = Settings(_env_file=None, llm_api_key="key", tts_model="test/tts", tts_voice="v")
    return OpenRouterSynthesizer(settings, transport=httpx.MockTransport(handler)), calls


def test_synthesis_requests_mp3_with_voice_and_retries(monkeypatch):
    tts, calls = synthesizer(
        [httpx.Response(503), httpx.Response(200, content=b"mp3")], monkeypatch
    )
    assert asyncio.run(tts.synthesize("привет")) == b"mp3"
    assert len(calls) == 2
    assert str(calls[0].url).endswith("/audio/speech")
    assert json.loads(calls[0].content) == {
        "model": "test/tts",
        "voice": "v",
        "input": "привет",
        "response_format": "mp3",
    }


def test_empty_synthesis_response_is_failure(monkeypatch):
    tts, _ = synthesizer([httpx.Response(200, content=b"")], monkeypatch)
    with pytest.raises(SpeechFailed):
        asyncio.run(tts.synthesize("привет"))


def say(client, text="привет", headers=MANAGER):
    return client.post("/speech/synthesis", headers=headers, json={"text": text})


def use_synthesizer(client, fake: FakeSynthesizer) -> None:
    client.app.state.speech = SpeechService(None, fake, max_audio_bytes=100, max_text_chars=10)


def test_synthesis_endpoint_returns_mp3(client):
    fake = FakeSynthesizer()
    use_synthesizer(client, fake)
    response = say(client, " привет ")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"mp3"
    assert fake.calls == ["привет"]


def test_synthesis_requires_user(client):
    use_synthesizer(client, FakeSynthesizer())
    assert codes(say(client, headers={})) == ["USER_REQUIRED"]


@pytest.mark.parametrize(
    ("text", "code"), [("   ", "SPEECH_TEXT_EMPTY"), ("x" * 11, "SPEECH_TEXT_TOO_LONG")]
)
def test_bad_text_never_reaches_provider(client, text, code):
    fake = FakeSynthesizer()
    use_synthesizer(client, fake)
    response = say(client, text)
    assert response.status_code == 400
    assert codes(response) == [code]
    assert fake.calls == []


def test_synthesis_provider_failure_is_502(client):
    use_synthesizer(client, FakeSynthesizer(SpeechFailed("HTTP 500")))
    response = say(client)
    assert response.status_code == 502
    assert codes(response) == ["SYNTHESIS_FAILED"]


def test_synthesis_without_key_reports_unavailable(client):
    response = say(client)
    assert response.status_code == 503
    assert codes(response) == ["SYNTHESIS_UNAVAILABLE"]
