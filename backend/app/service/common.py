from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.db.models import Campaign
from app.db.repositories import CampaignRepository
from app.domain.actors import Actor, require_role
from app.domain.enums import Role
from app.domain.lifecycle import ensure_editable
from app.service.mappers import campaign_header


async def get_campaign(session: AsyncSession, campaign_id: int) -> Campaign:
    campaign = await CampaignRepository(session).get(campaign_id)
    if campaign is None:
        raise not_found("campaignId", campaign_id)
    return campaign


async def editable_campaign(session: AsyncSession, actor: Actor, campaign_id: int) -> Campaign:
    require_role(actor, Role.MANAGER)
    campaign = await get_campaign(session, campaign_id)
    ensure_editable(campaign)
    return campaign


def info_snapshot(campaign: Campaign) -> dict[str, Any]:
    data = campaign_header(campaign)
    for key in ("id", "state", "published", "author", "lastEditAuthor"):
        data.pop(key)
    data = {
        key: value.isoformat() if isinstance(value, date) else value for key, value in data.items()
    }
    data["places"] = campaign.place_ids
    return data
