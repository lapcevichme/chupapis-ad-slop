"""Связь «кампания + логин → диалог» (docs/ours/chat-api.md §10).

У менеджера и модератора по одной кампании разные диалоги: иначе сообщение модератора отклонило бы
подтверждение, которое ждёт менеджер, а агент модератора помнил бы разговор с менеджером.
"""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.domain.audit import utcnow
from app.models import ChatSession


class SessionRegistry:
    """Запросы короткие и синхронные, поэтому из асинхронного кода они уходят в пул потоков."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    async def find(self, campaign_id: int, user: str) -> str | None:
        return await asyncio.to_thread(self._find, campaign_id, user)

    async def create(self, campaign_id: int | None, user: str) -> str:
        return await asyncio.to_thread(self._create, campaign_id, user)

    async def bind(self, session_id: str, campaign_id: int | None) -> None:
        await asyncio.to_thread(self._bind, session_id, campaign_id)

    def _find(self, campaign_id: int, user: str) -> str | None:
        with self.session_factory() as db:
            return db.scalar(
                select(ChatSession.session_id).where(ChatSession.campaign_id == campaign_id, ChatSession.user_login == user)
            )

    def _create(self, campaign_id: int | None, user: str) -> str:
        session_id = uuid.uuid4().hex
        with self.session_factory() as db:
            db.add(ChatSession(session_id=session_id, user_login=user, campaign_id=campaign_id, created_at=utcnow()))
            db.commit()
        return session_id

    def _bind(self, session_id: str, campaign_id: int | None) -> None:
        """Диалог новой кампании привязывается к ней, когда кампания сохранена в API."""
        if campaign_id is None:
            return
        with self.session_factory() as db:
            row = db.get(ChatSession, session_id)
            if row is None or row.campaign_id == campaign_id:
                return
            row.campaign_id = campaign_id
            try:
                db.commit()
            except IntegrityError:
                # У этого пользователя уже есть диалог по кампании: оставляем тот, что был первым.
                db.rollback()
