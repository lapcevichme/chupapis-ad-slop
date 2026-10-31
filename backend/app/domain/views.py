from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from app.core.errors import ApiError
from app.domain.enums import AudienceType, CampaignState, PlaceState, SegmentState, Topic


@dataclass(frozen=True, slots=True)
class TopicDto:
    value: Topic
    label: str


@dataclass(frozen=True, slots=True)
class TagDto:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class ChannelDto:
    id: int
    code: str
    description: str


@dataclass(frozen=True, slots=True)
class BannerTypeDto:
    id: int
    code: str
    description: str
    previewForm: str
    titleMaxLength: int
    textMaxLength: int
    channels: list[str]


@dataclass(frozen=True, slots=True)
class SegmentTypeDto:
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class SegmentDto:
    code: str
    name: str
    type: str
    state: SegmentState
    count: int


@dataclass(frozen=True, slots=True)
class PlaceDto:
    id: int
    code: str
    description: str
    defaultBanner: str | None
    state: PlaceState


@dataclass(frozen=True, slots=True)
class CampaignRef:
    id: int
    state: CampaignState
    published: bool
    author: str
    lastEditAuthor: str


@dataclass(frozen=True, slots=True)
class CampaignListItem:
    id: int
    name: str
    state: CampaignState
    published: bool
    topic: Topic
    startDate: date
    startTime: str
    endDate: date | None
    endTime: str | None


@dataclass(frozen=True, slots=True)
class CampaignHeader:
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


@dataclass(frozen=True, slots=True)
class Segments:
    included: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BannerDto:
    id: int
    campaignId: int
    name: str
    bannerTypeId: int
    content: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ContentDto:
    id: int
    campaignId: int
    name: str
    contentType: str
    content: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CreativeDto:
    id: int
    campaignId: int
    name: str
    bannerId: int
    contentId: int | None
    channelCode: str


@dataclass(frozen=True, slots=True)
class CampaignDetails(CampaignHeader):
    places: list[int]
    segments: Segments
    banners: list[BannerDto]
    contents: list[ContentDto]
    creatives: list[CreativeDto]


@dataclass(frozen=True, slots=True)
class ValidationReport:
    errors: list[ApiError]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class AuditRecord:
    entity: str
    entityId: int
    action: str
    changes: dict[str, Any] | None
    at: datetime
    actor: str
    comment: str | None


@dataclass(frozen=True, slots=True)
class CbroExportResponse:
    status: Literal["OK"]
    exportedAt: datetime
