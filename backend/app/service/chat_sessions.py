from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.errors import ApiError, DomainError, not_found
from app.db.database import Database
from app.db.models import Campaign, ChatSession
from app.domain.audit import utcnow
from app.domain.chat import ChatSummary


def _uuid(session_id: str) -> UUID:
    try:
        return UUID(session_id)
    except ValueError:
        raise not_found("sessionId", session_id) from None


class SessionRegistry:
    def __init__(self, database: Database):
        self.database = database

    async def find(self, campaign_id: int, user_id: UUID) -> str | None:
        async with self.database.unit_of_work() as uow:
            found = await uow.session.scalar(
                select(ChatSession.id).where(
                    ChatSession.campaign_id == campaign_id,
                    ChatSession.user_id == user_id,
                    ChatSession.archived_at.is_(None),
                )
            )
            return str(found) if found else None

    async def create(self, campaign_id: int | None, user_id: UUID) -> str:
        session_id = uuid4()
        async with self.database.unit_of_work() as uow:
            uow.session.add(
                ChatSession(
                    id=session_id, user_id=user_id, campaign_id=campaign_id, created_at=utcnow()
                )
            )
        return str(session_id)

    async def bind(self, session_id: str, campaign_id: int | None) -> None:
        if campaign_id is None:
            return
        try:
            async with self.database.unit_of_work() as uow:
                row = await uow.session.get(ChatSession, _uuid(session_id))
                if row is not None and row.archived_at is None and row.campaign_id != campaign_id:
                    row.campaign_id = campaign_id
        except IntegrityError:
            # Прежний диалог этого пользователя по кампании остаётся главным.
            return

    async def require(self, session_id: str, user_id: UUID | None = None) -> None:
        async with self.database.unit_of_work() as uow:
            row = await uow.session.get(ChatSession, _uuid(session_id))
            if row is None or row.archived_at is not None or (user_id and row.user_id != user_id):
                raise not_found("sessionId", session_id)

    async def list(self, user_id: UUID, archived: bool = False) -> list[ChatSummary]:
        async with self.database.unit_of_work() as uow:
            rows = (
                await uow.session.scalars(
                    select(ChatSession)
                    .where(
                        ChatSession.user_id == user_id,
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
                    str(row.id),
                    row.campaign_id,
                    campaigns.get(row.campaign_id or 0, "Новая кампания"),
                    row.created_at,
                    row.archived_at,
                )
                for row in rows
            ]

    async def archive(self, session_id: str, user_id: UUID) -> None:
        async with self.database.unit_of_work() as uow:
            row = await uow.session.get(ChatSession, _uuid(session_id))
            if row is None or row.user_id != user_id:
                raise not_found("sessionId", session_id)
            if row.archived_at is None:
                row.archived_at = utcnow()

    async def restore(self, session_id: str, user_id: UUID) -> None:
        try:
            async with self.database.unit_of_work() as uow:
                row = await uow.session.get(ChatSession, _uuid(session_id))
                if row is None or row.user_id != user_id:
                    raise not_found("sessionId", session_id)
                if row.archived_at is not None:
                    row.archived_at = None
                    await uow.flush()
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
