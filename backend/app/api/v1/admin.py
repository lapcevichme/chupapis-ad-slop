from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import ERROR_RESPONSES, UowDep, require
from app.api.schemas.auth import RoleUpdate, UserOut
from app.domain.enums import Role
from app.domain.users import CurrentUser, Permission, UserQuery
from app.service.admin import AdminUserService

router = APIRouter(prefix="/admin", tags=["admin"], responses=ERROR_RESPONSES)

UsersReader = Annotated[CurrentUser, Depends(require(Permission.USERS_READ))]
UsersBanner = Annotated[CurrentUser, Depends(require(Permission.USERS_BAN))]
RoleManager = Annotated[CurrentUser, Depends(require(Permission.USERS_MANAGE_ROLES))]


@router.get("/users", summary="Поиск пользователей, новые первыми")
async def list_users(
    admin: UsersReader,
    uow: UowDep,
    search: Annotated[
        str | None, Query(max_length=100, description="Часть почты или имени")
    ] = None,
    role: Role | None = None,
    banned: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserOut]:
    query = UserQuery(search=search, role=role, banned=banned, limit=limit, offset=offset)
    profiles = await AdminUserService(uow, admin).list_users(query)
    return [UserOut.from_domain(p) for p in profiles]


@router.post("/users/{user_id}/ban", summary="Заблокировать пользователя и завершить его сессии")
async def ban_user(user_id: UUID, admin: UsersBanner, uow: UowDep) -> UserOut:
    return UserOut.from_domain(await AdminUserService(uow, admin).ban(user_id))


@router.delete("/users/{user_id}/ban", summary="Снять блокировку")
async def unban_user(user_id: UUID, admin: UsersBanner, uow: UowDep) -> UserOut:
    return UserOut.from_domain(await AdminUserService(uow, admin).unban(user_id))


@router.put("/users/{user_id}/role", summary="Сменить роль пользователя")
async def set_role(user_id: UUID, payload: RoleUpdate, admin: RoleManager, uow: UowDep) -> UserOut:
    return UserOut.from_domain(await AdminUserService(uow, admin).set_role(user_id, payload.role))
