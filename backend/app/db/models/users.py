from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UuidPkMixin, pg_enum, utcnow
from app.domain.auth import ClientKind
from app.domain.enums import Role


class User(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    # Имя для входа в интерфейсе и в API: автор кампании и записи аудита показываются им.
    username: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[Role] = mapped_column(pg_enum(Role, "user_role"))
    banned_at: Mapped[datetime | None]
    # Растёт при бане и «выйти везде»: access-токены несут версию и умирают при расхождении.
    auth_version: Mapped[int] = mapped_column(default=1, server_default="1")

    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        Index("uq_users_username_lower", func.lower(username), unique=True),
    )


class AuthSession(UuidPkMixin, Base):
    """Одно устройство, где пользователь вошёл. Хранит хэш текущего refresh-токена."""

    __tablename__ = "auth_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    client: Mapped[ClientKind] = mapped_column(pg_enum(ClientKind, "client_kind"))
    user_agent: Mapped[str | None] = mapped_column(String(512))

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
