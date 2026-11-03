from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.db.models import Campaign, User
from app.db.repositories.campaigns import CampaignRepository
from app.domain.lifecycle import ensure_editable
from app.domain.users import CurrentUser, Permission, ensure_can
from app.service.mappers import campaign_header


async def get_campaign(session: AsyncSession, campaign_id: int) -> Campaign:
    campaign = await CampaignRepository(session).get(campaign_id)
    if campaign is None:
        raise not_found("campaignId", campaign_id)
    return campaign


async def editable_campaign(session: AsyncSession, user: CurrentUser, campaign_id: int) -> Campaign:
    ensure_can(user, Permission.CAMPAIGNS_WRITE)
    campaign = await get_campaign(session, campaign_id)
    ensure_editable(campaign)
    return campaign


async def user_row(session: AsyncSession, user: CurrentUser) -> User:
    """ORM-строка пользователя. Её уже загрузила проверка токена в этой же сессии, так что запроса не будет."""
    row = await session.get(User, user.id)
    assert row is not None
    return row


def info_snapshot(campaign: Campaign) -> dict[str, Any]:
    data = campaign_header(campaign)
    for key in ("id", "state", "published", "author", "lastEditAuthor"):
        data.pop(key)
    data = {
        key: value.isoformat() if isinstance(value, date) else value for key, value in data.items()
    }
    data["places"] = campaign.place_ids
    return data
