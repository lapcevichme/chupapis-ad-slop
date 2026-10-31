from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import CampaignRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.campaigns = CampaignRepository(session)

    async def flush(self) -> None:
        await self.session.flush()
