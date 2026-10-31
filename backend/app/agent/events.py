"""События SSE-потока чата (docs/ours/chat-api.md §1). Схемы попадают в openapi.json как ChatEvent*."""

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.errors import ApiError


class ChatEventMessageDelta(BaseModel):
    text: str


class ChatEventStep(BaseModel):
    id: str
    label: str
    status: Literal["running", "done", "failed"]


class SuggestionItem(BaseModel):
    label: str
    value: str
    group: str | None = None


class ChatEventSuggestions(BaseModel):
    items: list[SuggestionItem]


class ConfirmationOperation(BaseModel):
    kind: str
    label: str


class ConfirmationChange(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    field: str
    label: str
    from_: Any = Field(None, alias="from")
    to: Any = None


class ChatEventConfirmationRequired(BaseModel):
    id: str
    title: str
    operations: list[ConfirmationOperation]
    changes: list[ConfirmationChange]


class DraftValidation(BaseModel):
    errors: list[ApiError]
    warnings: list[str]


class ChatEventDraftUpdated(BaseModel):
    draft: dict[str, Any]
    validation: DraftValidation


class ChatEventCampaignUpdated(BaseModel):
    campaignId: int | None


class ChatEventWarning(BaseModel):
    """Предупреждение агента о спорном решении пользователя. Агент при этом не отказывается выполнять просьбу."""

    message: str
    severity: Literal["info", "warning"] = "warning"


class ChatEventError(BaseModel):
    code: str
    message: str


class ChatEventDone(BaseModel):
    pass


EVENT_MODELS: dict[str, type[BaseModel]] = {
    "message_delta": ChatEventMessageDelta,
    "step": ChatEventStep,
    "suggestions": ChatEventSuggestions,
    "confirmation_required": ChatEventConfirmationRequired,
    "draft_updated": ChatEventDraftUpdated,
    "campaign_updated": ChatEventCampaignUpdated,
    "warning": ChatEventWarning,
    "error": ChatEventError,
    "done": ChatEventDone,
}


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# --- Тела и ответы REST-части чата


class CreateSessionBody(BaseModel):
    campaignId: int | None = None


class SessionCreated(BaseModel):
    sessionId: str


class MessageBody(BaseModel):
    text: str


class ConfirmationBody(BaseModel):
    approved: bool
    comment: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class SessionSnapshot(BaseModel):
    campaignId: int | None
    messages: list[ChatMessage]
    draft: dict[str, Any] | None
    validation: DraftValidation
    pendingConfirmation: ChatEventConfirmationRequired | None
