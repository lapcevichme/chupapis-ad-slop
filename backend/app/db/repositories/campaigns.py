from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Banner, Campaign, CampaignPlace, Creative


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, campaign_id: int) -> Campaign | None:
        statement = (
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .options(
                selectinload(Campaign.tag_links),
                selectinload(Campaign.place_links).joinedload(CampaignPlace.place),
                selectinload(Campaign.segment_links),
                selectinload(Campaign.banners).joinedload(Banner.banner_type),
                selectinload(Campaign.contents),
                selectinload(Campaign.creatives)
                .joinedload(Creative.banner)
                .joinedload(Banner.banner_type),
                selectinload(Campaign.creatives).joinedload(Creative.content),
            )
        )
        return await self._session.scalar(statement)

    async def list(self) -> Sequence[Campaign]:
        return (await self._session.scalars(select(Campaign).order_by(Campaign.id))).all()
