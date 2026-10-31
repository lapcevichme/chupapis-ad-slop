from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app import models
from app.actor import Actor, get_actor, require_role
from app.db import get_session
from app.domain.enums import Role
from app.domain.lifecycle import ensure_editable
from app.errors import ErrorResponse, not_found
from app.schemas import api
from app.serializers import campaign_header

SessionDep = Annotated[Session, Depends(get_session)]
ActorDep = Annotated[Actor, Depends(get_actor)]

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Ошибки валидации или жизненного цикла"},
    404: {"model": ErrorResponse, "description": "ENTITY_NOT_FOUND"},
}


def get_campaign(session: Session, campaign_id: int) -> models.Campaign:
    campaign = session.get(models.Campaign, campaign_id)
    if campaign is None:
        raise not_found("campaignId", campaign_id)
    return campaign


def editable_campaign(session: Session, actor: Actor, campaign_id: int) -> models.Campaign:
    """Порядок проверок по §2.3: роль, существование, состояние."""
    require_role(actor, Role.MANAGER)
    campaign = get_campaign(session, campaign_id)
    ensure_editable(campaign)
    return campaign


def info_snapshot(c: models.Campaign) -> dict[str, Any]:
    data = api.CampaignHeader(**campaign_header(c)).model_dump(mode="json")
    for key in ("id", "state", "published", "author", "lastEditAuthor"):
        data.pop(key)
    data["places"] = c.place_ids
    return data
