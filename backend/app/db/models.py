from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Перечисления хранятся строками, а не нативными enum: так схема одинакова в SQLite и PostgreSQL.


class Topic(Base):
    __tablename__ = "topics"

    value: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    description: Mapped[str] = mapped_column(String(100))


class BannerType(Base):
    __tablename__ = "banner_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(String(100))
    preview_form: Mapped[str] = mapped_column(String(32))
    title_max_length: Mapped[int] = mapped_column(Integer)
    text_max_length: Mapped[int] = mapped_column(Integer)
    channels: Mapped[list[str]] = mapped_column(JSON)


class SegmentType(Base):
    __tablename__ = "segment_types"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class Segment(Base):
    __tablename__ = "segments"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(ForeignKey("segment_types.code"))
    state: Mapped[str] = mapped_column(String(16))
    count: Mapped[int] = mapped_column(BigInteger)


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(255))
    default_banner: Mapped[str | None] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(16))


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    marketing_name: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[str] = mapped_column(String(5))
    end_date: Mapped[date | None] = mapped_column(Date)
    end_time: Mapped[str | None] = mapped_column(String(5))
    topic: Mapped[str] = mapped_column(ForeignKey("topics.value"))
    keywords: Mapped[str | None] = mapped_column(String(512))
    audience_type: Mapped[str] = mapped_column(String(16))
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    initial_ctr: Mapped[float] = mapped_column(Float, default=15.0)
    state: Mapped[str] = mapped_column(String(32))
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    author: Mapped[str] = mapped_column(String(100))
    last_edit_author: Mapped[str] = mapped_column(String(100))

    tag_links: Mapped[list["CampaignTag"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="CampaignTag.position"
    )
    place_links: Mapped[list["CampaignPlace"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="CampaignPlace.position"
    )
    segment_links: Mapped[list["CampaignSegment"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="CampaignSegment.position"
    )
    banners: Mapped[list["Banner"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="Banner.id"
    )
    contents: Mapped[list["Content"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="Content.id"
    )
    creatives: Mapped[list["Creative"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="Creative.id"
    )

    @property
    def tag_ids(self) -> list[int]:
        return [link.tag_id for link in self.tag_links]

    @property
    def place_ids(self) -> list[int]:
        return [link.place_id for link in self.place_links]

    def segment_codes(self, kind: str) -> list[str]:
        return [link.segment_code for link in self.segment_links if link.kind == kind]


class CampaignTag(Base):
    __tablename__ = "campaign_tags"

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class CampaignPlace(Base):
    __tablename__ = "campaign_places"

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    place: Mapped[Place] = relationship(lazy="joined")


class CampaignSegment(Base):
    __tablename__ = "campaign_segments"

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    segment_code: Mapped[str] = mapped_column(ForeignKey("segments.code"), primary_key=True)
    # included | excluded
    kind: Mapped[str] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer, default=0)


class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    banner_type_id: Mapped[int] = mapped_column(ForeignKey("banner_types.id"))
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    banner_type: Mapped[BannerType] = relationship(lazy="joined")


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    content_type: Mapped[str] = mapped_column(String(16))
    content: Mapped[dict[str, Any]] = mapped_column(JSON)


class Creative(Base):
    __tablename__ = "creatives"
    __table_args__ = (UniqueConstraint("campaign_id", "banner_id", "channel_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    banner_id: Mapped[int] = mapped_column(ForeignKey("banners.id"))
    content_id: Mapped[int | None] = mapped_column(ForeignKey("contents.id"))
    channel_code: Mapped[str] = mapped_column(ForeignKey("channels.code"))
    # Связи нужны и для порядка удаления: креативы удаляются раньше баннеров и контента.
    banner: Mapped[Banner] = relationship(lazy="joined")
    content: Mapped[Content | None] = relationship()


class AuditEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Без внешнего ключа: журнал переживает удаление кампании.
    campaign_id: Mapped[int | None] = mapped_column(Integer, index=True)
    entity: Mapped[str] = mapped_column(String(16))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(16))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(DateTime)
    actor: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(Text)


class ChatSession(Base):
    """Диалог агента: у каждой пары «кампания + логин» он один (docs/contracts/chat.md §10).

    Само состояние диалога хранит checkpointer LangGraph, здесь только связь. У новой кампании
    campaign_id пустой, пока она не сохранена в API.
    """

    __tablename__ = "chat_sessions"
    __table_args__ = (UniqueConstraint("campaign_id", "user_login"),)

    session_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_login: Mapped[str] = mapped_column(String(100))
    # Без внешнего ключа: кампанию могут удалить, а диалог о ней остаётся.
    campaign_id: Mapped[int | None] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
