import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.errors import ApiError, DomainError, not_found
from app.db.database import Database
from app.db.models import Campaign, ChatSession
from app.domain.audit import utcnow
from app.domain.chat import ChatSummary


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
                if row is not None and row.archived_at is None and row.campaign_id != campaign_id:
                    row.campaign_id = campaign_id
        except IntegrityError:
            # The earlier chat of this user/campaign remains canonical.
            return

    async def require(self, session_id: str, user: str | None = None) -> None:
        async with self.database.unit_of_work() as uow:
            row = await uow.session.get(ChatSession, session_id)
            if row is None or row.archived_at is not None or (user and row.user_login != user):
                raise not_found("sessionId", session_id)

    async def list(self, user: str, archived: bool = False) -> list[ChatSummary]:
        async with self.database.unit_of_work() as uow:
            rows = (
                await uow.session.scalars(
                    select(ChatSession)
                    .where(
                        ChatSession.user_login == user,
                        ChatSession.archived_at.is_not(None)
                        if archived
                        else ChatSession.archived_at.is_(None),
                    )
                    .order_by(ChatSession.created_at.desc())
                )
            ).all()
            campaigns = dict((await uow.session.execute(select(Campaign.id, Campaign.name))).all())
            return [
                ChatSummary(
                    row.session_id,
                    row.archived_campaign_id if archived else row.campaign_id,
                    campaigns.get(
                        (row.archived_campaign_id if archived else row.campaign_id) or 0,
                        "Новая кампания",
                    ),
                    row.created_at,
                    row.archived_at,
                )
                for row in rows
            ]

    async def archive(self, session_id: str, user: str) -> None:
        async with self.database.unit_of_work() as uow:
            row = await uow.session.get(ChatSession, session_id)
            if row is None or row.user_login != user:
                raise not_found("sessionId", session_id)
            if row.archived_at is None:
                row.archived_campaign_id = row.campaign_id
                row.campaign_id = None
                row.archived_at = utcnow()

    async def restore(self, session_id: str, user: str) -> None:
        try:
            async with self.database.unit_of_work() as uow:
                row = await uow.session.get(ChatSession, session_id)
                if row is None or row.user_login != user:
                    raise not_found("sessionId", session_id)
                if row.archived_at is not None:
                    row.campaign_id = row.archived_campaign_id
                    row.archived_campaign_id = None
                    row.archived_at = None
        except IntegrityError as exc:
            raise DomainError(
                [
                    ApiError(
                        "CHAT_CONFLICT",
                        "У кампании уже есть новый диалог. Сначала удалите его, чтобы восстановить прежний.",
                    )
                ],
                409,
            ) from exc
