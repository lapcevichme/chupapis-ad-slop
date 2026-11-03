from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UuidPkMixin, utcnow


class ChatSession(UuidPkMixin, Base):
    """Диалог агента: у каждой пары «кампания + пользователь» активный диалог один (docs/contracts/chat.md §10).

    Состояние диалога хранит checkpointer LangGraph под thread_id = id, здесь только связь.
    У новой кампании campaign_id пустой, пока она не сохранена.
    """

    __tablename__ = "chat_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Кампанию могут удалить, а диалог о ней остаётся как диалог без кампании.
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    archived_at: Mapped[datetime | None]

    __table_args__ = (
        Index(
            "uq_chat_sessions_active",
            "user_id",
            "campaign_id",
            unique=True,
            postgresql_where=text("archived_at IS NULL"),
        ),
    )
