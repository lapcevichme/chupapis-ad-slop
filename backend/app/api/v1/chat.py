"""API чата (docs/ours/chat-api.md). Ответы на сообщения и подтверждения — поток SSE."""

from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import ERROR_RESPONSES, ActorDep
from app.api.sse import encode_events
from app.contracts import chat as events
from app.domain.chat import StreamEvent
from app.service.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"], responses=ERROR_RESPONSES)

SSE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {"text/event-stream": {}},
        "description": "Поток событий ChatEvent* (chat-api.md §1)",
    }
}


def get_chat(request: Request) -> ChatService:
    chat: ChatService = request.app.state.chat
    return chat


ChatDep = Annotated[ChatService, Depends(get_chat)]


def _stream(iterator: AsyncIterator[StreamEvent]) -> StreamingResponse:
    return StreamingResponse(
        encode_events(iterator),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("", response_model=events.SessionCreated, status_code=201)
async def create_chat_session(
    body: events.CreateSessionBody, chat: ChatDep, actor: ActorDep
) -> events.SessionCreated:
    session_id = await chat.create_session(body.campaignId, actor.login, actor.role or "")
    return events.SessionCreated(sessionId=session_id)


@router.get("/{session_id}", response_model=events.SessionSnapshot)
async def get_chat_session(session_id: str, chat: ChatDep, actor: ActorDep) -> dict[str, Any]:
    return await chat.snapshot(session_id, actor.login, actor.role or "")


@router.post("/{session_id}/messages", responses=SSE_RESPONSE, response_class=StreamingResponse)
async def send_chat_message(
    session_id: str, body: events.MessageBody, chat: ChatDep, actor: ActorDep
) -> StreamingResponse:
    return _stream(await chat.send_message(session_id, body.text, actor.login, actor.role or ""))


@router.post(
    "/{session_id}/confirmations/{confirmation_id}",
    responses=SSE_RESPONSE,
    response_class=StreamingResponse,
)
async def answer_chat_confirmation(
    session_id: str,
    confirmation_id: str,
    body: events.ConfirmationBody,
    chat: ChatDep,
    actor: ActorDep,
) -> StreamingResponse:
    return _stream(
        await chat.answer_confirmation(
            session_id, confirmation_id, body.approved, body.comment, actor.login, actor.role or ""
        )
    )


@router.post("/{session_id}/retry", responses=SSE_RESPONSE, response_class=StreamingResponse)
async def retry_chat_turn(session_id: str, chat: ChatDep, actor: ActorDep) -> StreamingResponse:
    return _stream(await chat.retry(session_id, actor.login, actor.role or ""))
