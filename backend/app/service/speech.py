import logging

from app.core.errors import DomainError, api_error, fail
from app.infra.live import LiveSessionFailed, LiveSessions, LiveSessionStarted
from app.infra.speech import SpeechFailed, Synthesizer, Transcriber

logger = logging.getLogger(__name__)

# Форматы, которые принимает /audio/transcriptions, по типам записи браузеров и обычных файлов.
AUDIO_FORMATS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
}


class SpeechService:
    def __init__(
        self,
        transcriber: Transcriber | None,
        synthesizer: Synthesizer | None,
        *,
        max_audio_bytes: int,
        max_text_chars: int,
        live_sessions: LiveSessions | None = None,
    ) -> None:
        self._live_sessions = live_sessions
        self._transcriber = transcriber
        self._synthesizer = synthesizer
        self.max_audio_bytes = max_audio_bytes
        self._max_text_chars = max_text_chars

    async def transcribe(self, audio: bytes, content_type: str | None) -> str:
        if self._transcriber is None:
            raise DomainError([api_error("TRANSCRIPTION_UNAVAILABLE")], status_code=503)
        if not audio:
            raise fail("AUDIO_EMPTY", "file")
        if len(audio) > self.max_audio_bytes:
            raise fail("AUDIO_TOO_LARGE", "file")
        mime = (content_type or "").split(";")[0].strip().lower()
        audio_format = AUDIO_FORMATS.get(mime)
        if audio_format is None:
            raise fail("AUDIO_FORMAT_UNSUPPORTED", "file")
        try:
            return await self._transcriber.transcribe(audio, audio_format)
        except SpeechFailed as exc:
            logger.warning("Transcription failed: %s", exc)
            raise DomainError([api_error("TRANSCRIPTION_FAILED")], status_code=502) from exc

    async def synthesize(self, text: str) -> bytes:
        if self._synthesizer is None:
            raise DomainError([api_error("SYNTHESIS_UNAVAILABLE")], status_code=503)
        spoken = text.strip()
        if not spoken:
            raise fail("SPEECH_TEXT_EMPTY", "text")
        if len(spoken) > self._max_text_chars:
            raise fail("SPEECH_TEXT_TOO_LONG", "text")
        try:
            return await self._synthesizer.synthesize(spoken)
        except SpeechFailed as exc:
            logger.warning("Speech synthesis failed: %s", exc)
            raise DomainError([api_error("SYNTHESIS_FAILED")], status_code=502) from exc

    async def start_live_session(self, offer_sdp: str) -> LiveSessionStarted:
        if self._live_sessions is None:
            raise DomainError([api_error("LIVE_VOICE_UNAVAILABLE")], status_code=503)
        try:
            return await self._live_sessions.create(offer_sdp)
        except LiveSessionFailed as exc:
            logger.warning("Live session failed: %s", exc)
            raise DomainError([api_error("LIVE_VOICE_FAILED")], status_code=502) from exc
