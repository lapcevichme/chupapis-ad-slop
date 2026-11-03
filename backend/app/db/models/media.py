from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UuidPkMixin, pg_enum, utcnow
from app.domain.media import MediaKind


class MediaObject(UuidPkMixin, Base):
    """Файл в S3. Имя (key) уникально и неизменно, поэтому его можно кешировать навсегда."""

    __tablename__ = "media_objects"

    key: Mapped[str] = mapped_column(String(255), unique=True)
    kind: Mapped[MediaKind] = mapped_column(pg_enum(MediaKind, "media_kind"), index=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())

    __table_args__ = (CheckConstraint("size_bytes > 0", name="size_positive"),)


class StudioDocument(Base):
    """Макет студии: JSON слоёв и его PNG. Идентификатор — хэш пары, повтор экспорта даёт ту же запись."""

    __tablename__ = "studio_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    render_id: Mapped[UUID] = mapped_column(ForeignKey("media_objects.id"))
    owner_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
