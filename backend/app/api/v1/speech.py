from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, UploadFile

from app.api.deps import ERROR_RESPONSES, ActorDep
from app.contracts.errors import ErrorResponse
from app.contracts.speech import SynthesisBody, Transcription
from app.core.errors import fail
from app.service.speech import SpeechService

router = APIRouter(
    prefix="/speech",
    tags=["speech"],
    responses={
        **ERROR_RESPONSES,
        502: {"model": ErrorResponse, "description": "TRANSCRIPTION_FAILED, SYNTHESIS_FAILED"},
        503: {
            "model": ErrorResponse,
            "description": "TRANSCRIPTION_UNAVAILABLE, SYNTHESIS_UNAVAILABLE",
        },
    },
)


def get_speech(request: Request) -> SpeechService:
    speech: SpeechService = request.app.state.speech
    return speech


SpeechDep = Annotated[SpeechService, Depends(get_speech)]


@router.post("/transcriptions", response_model=Transcription)
async def transcribe_speech(file: UploadFile, speech: SpeechDep, _actor: ActorDep) -> Transcription:
    # Размер проверяем до чтения в память: распознавание платное, а тело присылает клиент.
    if file.size is not None and file.size > speech.max_audio_bytes:
        raise fail("AUDIO_TOO_LARGE", "file")
    return Transcription(text=await speech.transcribe(await file.read(), file.content_type))


@router.post(
    "/synthesis",
    response_class=Response,
    responses={200: {"content": {"audio/mpeg": {}}, "description": "Озвученный текст, MP3"}},
)
async def synthesize_speech(body: SynthesisBody, speech: SpeechDep, _actor: ActorDep) -> Response:
    return Response(await speech.synthesize(body.text), media_type="audio/mpeg")
