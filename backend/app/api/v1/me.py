from fastapi import APIRouter

from app.api.deps import ERROR_RESPONSES, CurrentUserDep, UowDep
from app.api.schemas.auth import UserOut
from app.core.errors import fail
from app.service.mappers import to_profile

router = APIRouter(prefix="/users", tags=["users"], responses=ERROR_RESPONSES)


@router.get("/me", response_model=UserOut, summary="Текущий пользователь")
async def get_me(user: CurrentUserDep, uow: UowDep) -> UserOut:
    row = await uow.users.get(user.id)
    if row is None:
        raise fail("USER_NOT_FOUND", status=404)
    return UserOut.from_domain(to_profile(row))
