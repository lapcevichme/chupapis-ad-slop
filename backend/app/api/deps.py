from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends, Header, Request

from app.contracts.errors import ErrorResponse
from app.core.config import Settings
from app.core.errors import fail
from app.db.database import Database
from app.db.uow import UnitOfWork
from app.domain.actors import Actor
from app.domain.enums import Role
from app.service.campaigns import CampaignService
from app.service.children import CreativeService
from app.service.dictionaries import DictionaryService


def database(request: Request) -> Database:
    db: Database = request.app.state.db
    return db


async def unit_of_work(db: Annotated[Database, Depends(database)]) -> AsyncIterator[UnitOfWork]:
    async with db.unit_of_work() as uow:
        yield uow


UowDep = Annotated[UnitOfWork, Depends(unit_of_work, scope="function")]


def actor(
    x_user: Annotated[str | None, Header(alias="X-User")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
) -> Actor:
    if not x_user:
        raise fail("USER_REQUIRED")
    return Actor(x_user, Role(x_role) if x_role in set(Role) else None)


ActorDep = Annotated[Actor, Depends(actor)]
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Ошибки валидации или жизненного цикла"},
    404: {"model": ErrorResponse, "description": "ENTITY_NOT_FOUND"},
}


def settings(request: Request) -> Settings:
    value: Settings = request.app.state.settings
    return value


SettingsDep = Annotated[Settings, Depends(settings)]


def campaign_service(uow: UowDep, config: SettingsDep) -> CampaignService:
    return CampaignService(uow, media_base_url=config.media_base_url)


def creative_service(uow: UowDep, config: SettingsDep) -> CreativeService:
    return CreativeService(uow, media_base_url=config.media_base_url)


def dictionary_service(uow: UowDep) -> DictionaryService:
    return DictionaryService(uow)


CampaignServiceDep = Annotated[CampaignService, Depends(campaign_service)]
CreativeServiceDep = Annotated[CreativeService, Depends(creative_service)]
DictionaryServiceDep = Annotated[DictionaryService, Depends(dictionary_service)]
