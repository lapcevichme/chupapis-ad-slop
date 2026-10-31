"""DTO API кампаний (§3 task.md). Имена полей — как в контракте, в camelCase."""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AudienceType, CampaignState, Topic
from app.errors import ApiError
from app.schemas.creative_json import BannerContent, PromoContent

TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Справочники


class TopicDto(BaseModel):
    value: Topic
    label: str


class TagDto(BaseModel):
    id: int
    name: str


class ChannelDto(BaseModel):
    id: int
    code: str
    description: str


class BannerTypeDto(BaseModel):
    id: int
    code: str
    description: str
    previewForm: str
    titleMaxLength: int
    textMaxLength: int
    channels: list[str]


class SegmentTypeDto(BaseModel):
    code: str
    name: str


class SegmentDto(BaseModel):
    code: str
    name: str
    type: str
    state: Literal["ACTIVE", "NEW"]
    count: int


class PlaceDto(BaseModel):
    id: int
    code: str
    description: str
    defaultBanner: str | None
    state: Literal["ACTIVE", "INACTIVE"]


class PlaceCreate(Body):
    code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=255)


class TagCreate(Body):
    name: str = Field(min_length=1, max_length=100)


# --- Кампания


class TopicRef(BaseModel):
    value: Topic
    label: str | None = None


class IdRef(BaseModel):
    value: int
    label: str | None = None


class CampaignInfo(Body):
    """Тело POST/PUT /campaigns (CampaignInfoDto). PUT — полная замена шапки и мест."""

    name: str = Field(min_length=1, max_length=100)
    marketingName: str | None = Field(None, max_length=100)
    startDate: date
    startTime: str = Field(pattern=TIME_PATTERN, description="HH:mm, UTC")
    endDate: date | None = None
    endTime: str | None = Field(None, pattern=TIME_PATTERN, description="HH:mm, UTC")
    topic: TopicRef
    tags: list[IdRef] = Field(default_factory=list)
    keywords: str | None = Field(None, max_length=512, description="Через ';'")
    audienceType: AudienceType
    weight: float = Field(0.0, ge=0)
    initialCtr: float = Field(15.0, ge=0, le=100)
    places: list[IdRef] = Field(min_length=1)


class CampaignRef(BaseModel):
    """Короткий ответ на запись и переходы жизненного цикла."""

    id: int
    state: CampaignState
    published: bool
    author: str
    lastEditAuthor: str


class CampaignListItem(BaseModel):
    id: int
    name: str
    state: CampaignState
    published: bool
    topic: Topic
    startDate: date
    startTime: str
    endDate: date | None
    endTime: str | None


class CampaignHeader(BaseModel):
    id: int
    name: str
    marketingName: str | None
    startDate: date
    startTime: str
    endDate: date | None
    endTime: str | None
    topic: Topic
    tags: list[int]
    keywords: str | None
    state: CampaignState
    published: bool
    audienceType: AudienceType
    weight: float
    initialCtr: float
    author: str
    lastEditAuthor: str


class Segments(Body):
    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)


# --- Дочерние сущности


class BannerCreate(Body):
    name: str = Field(min_length=1, max_length=100)
    bannerTypeId: int
    content: BannerContent


class BannerDto(BaseModel):
    id: int
    campaignId: int
    name: str
    bannerTypeId: int
    content: dict[str, Any]


class ContentCreate(Body):
    name: str = Field(min_length=1, max_length=100)
    contentType: Literal["PROMO"] = "PROMO"
    content: PromoContent


class ContentDto(BaseModel):
    id: int
    campaignId: int
    name: str
    contentType: str
    content: dict[str, Any]


class CreativeCreate(Body):
    name: str = Field(min_length=1, max_length=100)
    bannerId: int
    contentId: int | None = None
    channelCode: str = Field(description="iOS | ANDROID | WEB, регистр важен")


class CreativeDto(BaseModel):
    id: int
    campaignId: int
    name: str
    bannerId: int
    contentId: int | None
    channelCode: str


class CampaignDetails(CampaignHeader):
    places: list[int]
    segments: Segments
    banners: list[BannerDto]
    contents: list[ContentDto]
    creatives: list[CreativeDto]


# --- Проверка, аудит, переходы


class ValidationReport(BaseModel):
    errors: list[ApiError]
    warnings: list[str]


class AuditRecord(BaseModel):
    entity: str
    entityId: int
    action: str
    changes: dict[str, Any] | None
    at: datetime
    actor: str
    comment: str | None


class DeclineBody(Body):
    # Необязателен в схеме, чтобы роль проверялась раньше комментария; пустой даёт DECLINE_COMMENT_REQUIRED.
    comment: str | None = None


class CbroExportRequest(Body):
    campaignId: int


class CbroExportResponse(BaseModel):
    status: Literal["OK"]
    exportedAt: datetime
