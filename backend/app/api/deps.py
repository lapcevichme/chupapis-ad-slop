from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import Depends, Header, Request

from app.contracts.errors import ErrorResponse
from app.core.errors import fail
from app.db.database import Database
from app.db.uow import UnitOfWork
from app.domain.actors import Actor
from app.domain.enums import Role


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
