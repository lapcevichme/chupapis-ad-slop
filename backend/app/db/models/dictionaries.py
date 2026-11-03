from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, pg_enum
from app.domain.enums import PlaceState, SegmentState


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
    channel_links: Mapped[list["BannerTypeChannel"]] = relationship(
        lazy="selectin", order_by="BannerTypeChannel.position", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "title_max_length > 0 AND text_max_length > 0", name="max_lengths_positive"
        ),
    )

    @property
    def channels(self) -> list[str]:
        return [link.channel_code for link in self.channel_links]


class BannerTypeChannel(Base):
    """Каналы, в которых показывается тип баннера."""

    __tablename__ = "banner_type_channels"

    banner_type_id: Mapped[int] = mapped_column(
        ForeignKey("banner_types.id", ondelete="CASCADE"), primary_key=True
    )
    channel_code: Mapped[str] = mapped_column(
        ForeignKey("channels.code", onupdate="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, default=0)


class SegmentType(Base):
    __tablename__ = "segment_types"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class Segment(Base):
    __tablename__ = "segments"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(ForeignKey("segment_types.code"), index=True)
    state: Mapped[SegmentState] = mapped_column(pg_enum(SegmentState, "segment_state"))
    count: Mapped[int] = mapped_column(BigInteger)

    __table_args__ = (CheckConstraint("count >= 0", name="count_non_negative"),)


class Place(Base):
    __tablename__ = "places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(255))
    default_banner: Mapped[str | None] = mapped_column(
        ForeignKey("banner_types.code", onupdate="CASCADE")
    )
    state: Mapped[PlaceState] = mapped_column(pg_enum(PlaceState, "place_state"))
