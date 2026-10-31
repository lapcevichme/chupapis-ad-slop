import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.database import Database
from app.db.models import ChatSession
from app.domain.audit import utcnow


class SessionRegistry:
    def __init__(self, database: Database):
        self.database = database

    async def find(self, campaign_id: int, user: str) -> str | None:
        async with self.database.unit_of_work() as uow:
            return await uow.session.scalar(
                select(ChatSession.session_id).where(
                    ChatSession.campaign_id == campaign_id,
                    ChatSession.user_login == user,
                )
            )

    async def create(self, campaign_id: int | None, user: str) -> str:
        session_id = uuid.uuid4().hex
        async with self.database.unit_of_work() as uow:
            uow.session.add(
                ChatSession(
                    session_id=session_id,
                    user_login=user,
                    campaign_id=campaign_id,
                    created_at=utcnow(),
                )
            )
        return session_id

    async def bind(self, session_id: str, campaign_id: int | None) -> None:
        if campaign_id is None:
            return
        try:
            async with self.database.unit_of_work() as uow:
                row = await uow.session.get(ChatSession, session_id)
                if row is not None and row.campaign_id != campaign_id:
                    row.campaign_id = campaign_id
        except IntegrityError:
            # The earlier chat of this user/campaign remains canonical.
            return
