from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.core.errors import fail, unauthorized
from app.core.security.passwords import hash_password, needs_rehash, verify_password
from app.core.security.tokens import AccessClaims, RefreshToken, TokenCodec
from app.db.models import AuthSession, User
from app.db.uow import UnitOfWork
from app.domain.auth import ClientKind, IssuedTokens
from app.domain.enums import Role
from app.domain.events import Topic
from app.domain.users import CurrentUser, normalize_email

_USER_AGENT_MAX = 512


class AuthService:
    def __init__(
        self,
        uow: UnitOfWork,
        codec: TokenCodec,
        *,
        refresh_ttl: timedelta,
        registration_enabled: bool = True,
    ) -> None:
        self._uow = uow
        self._codec = codec
        self._refresh_ttl = refresh_ttl
        self._registration_enabled = registration_enabled

    async def register(
        self,
        *,
        email: str,
        password: str,
        username: str,
        client: ClientKind,
        user_agent: str | None,
    ) -> IssuedTokens:
        if not self._registration_enabled:
            raise fail("REGISTRATION_DISABLED", status=403)
        email = normalize_email(email)
        if await self._uow.users.get_by_email(email) is not None:
            raise fail("EMAIL_TAKEN", "email", status=409)
        if await self._uow.users.get_by_username(username) is not None:
            raise fail("USERNAME_TAKEN", "username", status=409)

        # Открытая регистрация создаёт менеджера: модераторов и админов заводит админ или CLI.
        user = User(
            email=email,
            username=username,
            password_hash=await hash_password(password),
            role=Role.MANAGER,
        )
        self._uow.users.add(user)
        try:
            await self._uow.flush()
        except IntegrityError as exc:
            # Две регистрации прошли проверку выше одновременно, решил уникальный индекс.
            raise fail("EMAIL_TAKEN", "email", status=409) from exc

        self._uow.outbox.add(Topic.USER_REGISTERED, {"user_id": str(user.id), "email": email})
        return await self._open_session(user, client, user_agent)

    async def login(
        self,
        *,
        email: str,
        password: str,
        client: ClientKind,
        user_agent: str | None,
    ) -> IssuedTokens:
        user = await self._uow.users.get_by_email(normalize_email(email))
        valid = await verify_password(password, user.password_hash if user else None)
        if user is None or not valid:
            raise unauthorized("WRONG_CREDENTIALS")
        if user.banned_at is not None:
            raise fail("ACCOUNT_BANNED", status=403)

        if needs_rehash(user.password_hash):
            user.password_hash = await hash_password(password)
        return await self._open_session(user, client, user_agent)

    async def refresh(self, raw_token: str, *, csrf_token: str | None) -> IssuedTokens:
        token = RefreshToken.parse(raw_token)
        session = await self._uow.sessions.get_for_update(token.session_id)
        now = datetime.now(UTC)
        if session is None or session.revoked_at is not None or session.expires_at <= now:
            raise unauthorized("SESSION_REVOKED")
        if session.client is ClientKind.WEB and not self._codec.csrf_matches(raw_token, csrf_token):
            raise fail("CSRF_FAILED", status=403)
        if not token.matches(session.token_hash):
            session.revoked_at = now
            raise unauthorized("REFRESH_TOKEN_REUSED", keep_changes=True)

        user = await self._uow.users.get(session.user_id)
        if user is None or user.banned_at is not None:
            session.revoked_at = now
            raise unauthorized("SESSION_REVOKED")

        rotated = RefreshToken.new(session.id)
        session.token_hash = rotated.hash
        session.last_used_at = now
        session.expires_at = now + self._refresh_ttl
        return self._issue(user, rotated, now)

    async def logout(self, raw_token: str) -> None:
        """Idempotent: an unknown or already revoked token is not an error."""
        token = RefreshToken.parse(raw_token)
        session = await self._uow.sessions.get_for_update(token.session_id)
        if session is not None and session.revoked_at is None and token.matches(session.token_hash):
            session.revoked_at = datetime.now(UTC)

    async def logout_everywhere(self, user_id: UUID) -> None:
        user = await self._uow.users.get(user_id, for_update=True)
        if user is None:
            raise fail("USER_NOT_FOUND", status=404)
        user.auth_version += 1
        await self._uow.sessions.revoke_all(user.id, now=datetime.now(UTC))

    async def _open_session(
        self, user: User, client: ClientKind, user_agent: str | None
    ) -> IssuedTokens:
        now = datetime.now(UTC)
        token = RefreshToken.new(uuid4())
        self._uow.sessions.add(
            AuthSession(
                id=token.session_id,
                user_id=user.id,
                token_hash=token.hash,
                client=client,
                user_agent=user_agent[:_USER_AGENT_MAX] if user_agent else None,
                created_at=now,
                last_used_at=now,
                expires_at=now + self._refresh_ttl,
            )
        )
        await self._uow.flush()
        return self._issue(user, token, now)

    def _issue(self, user: User, token: RefreshToken, now: datetime) -> IssuedTokens:
        raw_refresh = str(token)
        return IssuedTokens(
            access_token=self._codec.issue_access(
                user_id=user.id,
                session_id=token.session_id,
                auth_version=user.auth_version,
                now=now,
            ),
            refresh_token=raw_refresh,
            csrf_token=self._codec.csrf_for(raw_refresh),
            expires_in=int(self._codec.access_ttl.total_seconds()),
        )


async def resolve_current_user(uow: UnitOfWork, claims: AccessClaims) -> CurrentUser:
    """Один запрос по первичному ключу на каждый запрос API: ловит баны, смену ролей и «выйти везде»."""
    user = await uow.users.get(claims.user_id)
    if user is None or user.auth_version != claims.auth_version:
        raise unauthorized("SESSION_REVOKED")
    if user.banned_at is not None:
        raise fail("ACCOUNT_BANNED", status=403)
    return CurrentUser(
        id=user.id, username=user.username, role=user.role, session_id=claims.session_id
    )
