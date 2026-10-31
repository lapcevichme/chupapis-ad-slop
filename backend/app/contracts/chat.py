from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import ApiError


class ChatEventMessageDelta(BaseModel):
    text: str


class ChatEventStep(BaseModel):
    id: str
    label: str
    status: Literal["running", "done", "failed"]


class SuggestionOption(BaseModel):
    label: str
    value: str
    description: str | None = None


class SuggestionQuestion(BaseModel):
    header: str
    question: str
    # Пусто — открытый вопрос голосового режима: человек отвечает своими словами.
    options: list[SuggestionOption]
    multiSelect: bool = False


class ChatEventSuggestions(BaseModel):
    """Опросник: варианты к каждому вопросу и поле для своего ответа, его фронт добавляет сам."""

    questions: list[SuggestionQuestion]


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


# --- Тела и ответы REST-части чата


class CreateSessionBody(BaseModel):
    campaignId: int | None = None


class SessionCreated(BaseModel):
    sessionId: str


class MessageBody(BaseModel):
    text: str
    voice: bool = False


class ConfirmationBody(BaseModel):
    approved: bool
    comment: str | None = None
    voice: bool = False


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class SessionSnapshot(BaseModel):
    campaignId: int | None
    messages: list[ChatMessage]
    draft: dict[str, Any] | None
    validation: DraftValidation
    pendingConfirmation: ChatEventConfirmationRequired | None
