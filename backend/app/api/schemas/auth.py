from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import Role
from app.domain.users import UserProfile


class RequestModel(BaseModel):
    """Тела запросов: лишние поля — ошибка, чтобы опечатки клиента не проходили молча."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RegisterRequest(RequestModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


class LoginRequest(RequestModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class TokenPair(BaseModel):
    """`refresh_token` пуст у веб-клиентов: они получают его как httpOnly-cookie вместе с читаемой
    cookie `csrf_token`, которую нужно повторить в заголовке `X-CSRF-Token`."""

    access_token: str
    refresh_token: str | None = None
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - тип токена OAuth2, не секрет
    expires_in: int = Field(..., description="Срок жизни access-токена в секундах")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    role: Role
    banned: bool

    @classmethod
    def from_domain(cls, profile: UserProfile) -> Self:
        return cls(
            id=str(profile.id),
            email=profile.email,
            username=profile.username,
            role=profile.role,
            banned=profile.is_banned,
        )


class RoleUpdate(RequestModel):
    role: Role
