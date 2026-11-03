import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID

import jwt

from app.core.config import Settings
from app.core.errors import unauthorized

_ACCESS_CLAIMS = ["sub", "sid", "av", "typ", "iat", "exp"]


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: UUID
    session_id: UUID
    auth_version: int


class TokenCodec:
    """
    Signs and checks short-lived JWT access tokens and derives CSRF tokens.
    Refresh tokens are opaque (see `RefreshToken`) and live in the `auth_sessions` table.
    """

    def __init__(
        self,
        *,
        private_key: str,
        public_key: str,
        algorithm: str,
        access_ttl: timedelta,
        csrf_key: bytes,
    ) -> None:
        self._private_key = private_key
        self._public_key = public_key
        self._algorithm = algorithm
        self.access_ttl = access_ttl
        self._csrf_key = csrf_key

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        if settings.jwt_private_key is None or settings.jwt_public_key is None:
            raise RuntimeError("JWT keys are not configured")
        return cls(
            private_key=settings.jwt_private_key.get_secret_value(),
            public_key=settings.jwt_public_key,
            algorithm=settings.jwt_algo,
            access_ttl=timedelta(seconds=settings.access_ttl),
            csrf_key=settings.csrf_hmac_key.get_secret_value().encode(),
        )

    def issue_access(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        auth_version: int,
        now: datetime | None = None,
    ) -> str:
        issued_at = now or datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "sid": str(session_id),
            "av": auth_version,
            "typ": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + self.access_ttl).timestamp()),
        }
        return jwt.encode(payload, self._private_key, algorithm=self._algorithm)

    def decode_access(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self._algorithm],
                options={"require": _ACCESS_CLAIMS},
            )
        except jwt.ExpiredSignatureError as exc:
            raise unauthorized("TOKEN_EXPIRED") from exc
        except jwt.PyJWTError as exc:
            raise unauthorized("INVALID_TOKEN") from exc

        if payload["typ"] != "access":
            raise unauthorized("INVALID_TOKEN")
        try:
            return AccessClaims(
                user_id=UUID(payload["sub"]),
                session_id=UUID(payload["sid"]),
                auth_version=int(payload["av"]),
            )
        except (TypeError, ValueError) as exc:
            raise unauthorized("INVALID_TOKEN") from exc

    def csrf_for(self, refresh_token: str) -> str:
        return hmac.new(self._csrf_key, refresh_token.encode(), hashlib.sha256).hexdigest()

    def csrf_matches(self, refresh_token: str, csrf_token: str | None) -> bool:
        if not csrf_token:
            return False
        return hmac.compare_digest(self.csrf_for(refresh_token), csrf_token)


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """`<session id>.<random secret>`; only a SHA-256 of the secret is stored."""

    session_id: UUID
    secret: str

    @classmethod
    def new(cls, session_id: UUID) -> Self:
        return cls(session_id=session_id, secret=secrets.token_urlsafe(32))

    @classmethod
    def parse(cls, raw: str) -> Self:
        session_part, _, secret = raw.partition(".")
        try:
            session_id = UUID(session_part)
        except ValueError as exc:
            raise unauthorized("INVALID_TOKEN") from exc
        if not secret:
            raise unauthorized("INVALID_TOKEN")
        return cls(session_id=session_id, secret=secret)

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.secret.encode()).hexdigest()

    def matches(self, stored_hash: str) -> bool:
        return hmac.compare_digest(self.hash, stored_hash)

    def __str__(self) -> str:
        return f"{self.session_id}.{self.secret}"
