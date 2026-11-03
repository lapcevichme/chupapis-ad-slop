from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.campaigns import CampaignRepository
from app.db.repositories.outbox import OutboxRepository
from app.db.repositories.sessions import SessionRepository
from app.db.repositories.users import UserRepository


class UnitOfWork:
    """Одна сессия = одна транзакция + репозитории на ней.
    Сервисы делают только `flush()`; коммитит владелец UoW (зависимость запроса, воркер, CLI)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.sessions = SessionRepository(session)
        self.outbox = OutboxRepository(session)
        self.campaigns = CampaignRepository(session)

    async def flush(self) -> None:
        await self.session.flush()
