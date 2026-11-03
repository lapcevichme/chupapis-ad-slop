from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, pg_enum
from app.db.models.dictionaries import BannerType, Place
from app.db.models.users import User
from app.domain.enums import AudienceType, CampaignState, ContentType, SegmentKind


def _children(order_by: str) -> Any:
    """Кампания всегда читается целиком, поэтому связи грузит репозиторий явно, а lazy="raise" запрещает
    неявный I/O. Каскадное удаление делает база (ON DELETE CASCADE), ORM детей не подгружает."""
    return relationship(
        lazy="raise", cascade="all, delete-orphan", passive_deletes=True, order_by=order_by
    )


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    # Идентификаторы из кейса (101, 102, ...) задаёт сид, новые выдаёт последовательность.
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    marketing_name: Mapped[str | None] = mapped_column(String(100))
    # Показ начинается и заканчивается в UTC; API отдаёт дату и время раздельно.
    start_at: Mapped[datetime]
    end_at: Mapped[datetime | None]
    topic: Mapped[str] = mapped_column(ForeignKey("topics.value"), index=True)
    keywords: Mapped[str | None] = mapped_column(String(512))
    audience_type: Mapped[AudienceType] = mapped_column(pg_enum(AudienceType, "audience_type"))
    weight: Mapped[float] = mapped_column(default=0.0, server_default="0")
    initial_ctr: Mapped[float] = mapped_column(default=15.0, server_default="15")
    state: Mapped[CampaignState] = mapped_column(pg_enum(CampaignState, "campaign_state"))
    published: Mapped[bool] = mapped_column(default=False, server_default="false")
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    last_editor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    author: Mapped[User] = relationship(lazy="joined", foreign_keys=[author_id])
    last_editor: Mapped[User] = relationship(lazy="joined", foreign_keys=[last_editor_id])

    tag_links: Mapped[list["CampaignTag"]] = _children("CampaignTag.position")
    place_links: Mapped[list["CampaignPlace"]] = _children("CampaignPlace.position")
    segment_links: Mapped[list["CampaignSegment"]] = _children("CampaignSegment.position")
    banners: Mapped[list["Banner"]] = _children("Banner.id")
    contents: Mapped[list["Content"]] = _children("Content.id")
    creatives: Mapped[list["Creative"]] = _children("Creative.id")

    __table_args__ = (
        CheckConstraint("end_at IS NULL OR end_at > start_at", name="period_valid"),
        CheckConstraint("weight >= 0", name="weight_non_negative"),
        CheckConstraint("initial_ctr >= 0 AND initial_ctr <= 100", name="initial_ctr_range"),
        # Живая кампания остаётся опубликованной, пока правки идут через модерацию, поэтому
        # запрещено только одно: опубликованная остановленная или архивная.
        CheckConstraint(
            "NOT published OR state NOT IN ('STOPPED', 'ARCHIVED')", name="published_state"
        ),
        Index("ix_campaigns_state", "state"),
        Index("ix_campaigns_start_at", "start_at"),
    )

    @property
    def tag_ids(self) -> list[int]:
        return [link.tag_id for link in self.tag_links]

    @property
    def place_ids(self) -> list[int]:
        return [link.place_id for link in self.place_links]

    def segment_codes(self, kind: SegmentKind) -> list[str]:
        return [link.segment_code for link in self.segment_links if link.kind == kind]


class CampaignTag(Base):
    __tablename__ = "campaign_tags"

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True, index=True)
    position: Mapped[int] = mapped_column(SmallInteger, default=0)


class CampaignPlace(Base):
    __tablename__ = "campaign_places"

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), primary_key=True, index=True)
    position: Mapped[int] = mapped_column(SmallInteger, default=0)
    place: Mapped[Place] = relationship(lazy="joined")


class CampaignSegment(Base):
    __tablename__ = "campaign_segments"

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    segment_code: Mapped[str] = mapped_column(
        ForeignKey("segments.code"), primary_key=True, index=True
    )
    kind: Mapped[SegmentKind] = mapped_column(pg_enum(SegmentKind, "segment_kind"))
    position: Mapped[int] = mapped_column(SmallInteger, default=0)


class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    banner_type_id: Mapped[int] = mapped_column(ForeignKey("banner_types.id"), index=True)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    banner_type: Mapped[BannerType] = relationship(lazy="joined")

    __table_args__ = (
        # Пара нужна креативам: составной внешний ключ не даст связать баннер чужой кампании.
        UniqueConstraint("campaign_id", "id", name="uq_banners_campaign_id_id"),
    )


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    content_type: Mapped[ContentType] = mapped_column(pg_enum(ContentType, "content_type"))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)

    __table_args__ = (UniqueConstraint("campaign_id", "id", name="uq_contents_campaign_id_id"),)


class Creative(Base):
    __tablename__ = "creatives"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    banner_id: Mapped[int] = mapped_column()
    content_id: Mapped[int | None] = mapped_column()
    channel_code: Mapped[str] = mapped_column(ForeignKey("channels.code"))
    banner: Mapped[Banner] = relationship(
        lazy="joined", primaryjoin="Creative.banner_id == Banner.id", foreign_keys=[banner_id]
    )
    content: Mapped[Content | None] = relationship(
        primaryjoin="Creative.content_id == Content.id", foreign_keys=[content_id]
    )

    __table_args__ = (
        # Баннер и контент креатива принадлежат той же кампании, что и он сам.
        ForeignKeyConstraint(
            ["campaign_id", "banner_id"],
            ["banners.campaign_id", "banners.id"],
            name="fk_creatives_banner_same_campaign",
        ),
        ForeignKeyConstraint(
            ["campaign_id", "content_id"],
            ["contents.campaign_id", "contents.id"],
            name="fk_creatives_content_same_campaign",
        ),
        UniqueConstraint("campaign_id", "banner_id", "channel_code", name="uq_creatives_slot"),
        Index("ix_creatives_banner_id", "banner_id"),
        Index("ix_creatives_content_id", "content_id"),
    )
