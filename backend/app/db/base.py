from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Имена ограничений и индексов детерминированы: миграции читаются без шума, а downgrade удаляет по имени.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Все моменты времени хранятся как timestamptz: без зон «10:00» в базе значит неизвестно что.
    type_annotation_map = {datetime: DateTime(timezone=True)}  # noqa: RUF012 - читает SQLAlchemy


def pg_enum[E: StrEnum](enum: type[E], name: str) -> Enum:
    """Нативный enum Postgres со значениями ("campaignManager"), а не с именами членов ("MANAGER")."""
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


class UuidPkMixin:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampMixin:
    # Значения выставляет и Python: после flush они уже известны, и чтение не вызывает ленивый refresh
    # (в async он упал бы с MissingGreenlet).
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=utcnow, onupdate=utcnow, server_default=func.now()
    )
