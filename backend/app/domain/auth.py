from dataclasses import dataclass
from enum import StrEnum


class ClientKind(StrEnum):
    """`web` хранит refresh-токен в httpOnly-cookie под защитой CSRF; `mobile` получает его в теле ответа."""

    WEB = "web"
    MOBILE = "mobile"


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    csrf_token: str
    expires_in: int
