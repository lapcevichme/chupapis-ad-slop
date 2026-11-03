"""Регистрация, вход, ротация refresh-токена, бан и права ролей."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.enums import Role
from app.main import create_app
from tests.conftest import ANONYMOUS, build_settings, codes, initialize_database

PASSWORD = "correct-horse-battery"


def register(client, email="new@example.com", username="newbie", mobile=True):
    headers = {"X-Client": "mobile"} if mobile else {}
    return client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "username": username},
        headers=ANONYMOUS | headers,
    )


def bearer(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_register_creates_manager_and_signs_in(client):
    response = register(client)
    assert response.status_code == 201
    tokens = response.json()
    assert tokens["refresh_token"] and tokens["token_type"] == "bearer"
    me = client.get("/users/me", headers=bearer(tokens))
    assert me.json() | {"id": None} == {
        "id": None,
        "email": "new@example.com",
        "username": "newbie",
        "role": "campaignManager",
        "banned": False,
    }
    # Новый менеджер видит кампании и может завести свою.
    assert client.get("/campaigns", headers=bearer(tokens)).status_code == 200


def test_duplicate_email_and_username_are_conflicts(client):
    assert register(client).status_code == 201
    again = register(client, username="other")
    assert again.status_code == 409 and codes(again) == ["EMAIL_TAKEN"]
    clash = register(client, email="x@example.com", username="NEWBIE")
    assert clash.status_code == 409 and codes(clash) == ["USERNAME_TAKEN"]


def test_login_and_wrong_credentials(client):
    register(client)
    ok = client.post(
        "/auth/login",
        json={"email": "NEW@example.com", "password": PASSWORD},
        headers=ANONYMOUS | {"X-Client": "mobile"},
    )
    assert ok.status_code == 200
    bad = client.post(
        "/auth/login",
        json={"email": "new@example.com", "password": "wrong-password"},
        headers=ANONYMOUS,
    )
    assert bad.status_code == 401 and codes(bad) == ["WRONG_CREDENTIALS"]
    unknown = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}, headers=ANONYMOUS
    )
    assert codes(unknown) == ["WRONG_CREDENTIALS"]


def test_garbage_token_is_rejected(client):
    response = client.get("/campaigns", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401 and codes(response) == ["INVALID_TOKEN"]


def test_refresh_rotates_and_reuse_kills_the_session(client):
    first = register(client).json()
    rotated = client.post(
        "/auth/refresh", headers=ANONYMOUS | {"Authorization": f"Bearer {first['refresh_token']}"}
    )
    assert rotated.status_code == 200
    second = rotated.json()
    assert second["refresh_token"] != first["refresh_token"]

    # Старый токен пришёл снова: его скопировали, поэтому сессия отзывается целиком.
    reused = client.post(
        "/auth/refresh", headers=ANONYMOUS | {"Authorization": f"Bearer {first['refresh_token']}"}
    )
    assert reused.status_code == 401 and codes(reused) == ["REFRESH_TOKEN_REUSED"]
    # Отзыв сохранился, хотя запрос закончился ошибкой (keep_changes).
    after = client.post(
        "/auth/refresh", headers=ANONYMOUS | {"Authorization": f"Bearer {second['refresh_token']}"}
    )
    assert after.status_code == 401 and codes(after) == ["SESSION_REVOKED"]


def test_web_client_uses_cookie_and_csrf():
    app = create_app(build_settings(refresh_cookie_path="/auth"))
    with TestClient(app) as web:
        web.portal.call(initialize_database, app)
        response = register(web, mobile=False)
        assert response.status_code == 201 and response.json()["refresh_token"] is None
        csrf = web.cookies.get("csrf_token")
        assert csrf and web.cookies.get("refresh_token")

        missing = web.post("/auth/refresh", headers=ANONYMOUS)
        assert missing.status_code == 403 and codes(missing) == ["CSRF_FAILED"]
        ok = web.post("/auth/refresh", headers=ANONYMOUS | {"X-CSRF-Token": csrf})
        assert ok.status_code == 200 and ok.json()["refresh_token"] is None


def test_logout_revokes_the_session(client):
    tokens = register(client).json()
    refresh = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    assert client.post("/auth/logout", headers=refresh).status_code == 204
    assert client.post("/auth/logout", headers=refresh).status_code == 204  # идемпотентно
    again = client.post("/auth/refresh", headers=refresh)
    assert codes(again) == ["SESSION_REVOKED"]


def test_logout_all_kills_issued_access_tokens(client):
    tokens = register(client).json()
    assert client.post("/auth/logout-all", headers=bearer(tokens)).status_code == 204
    me = client.get("/users/me", headers=bearer(tokens))
    assert me.status_code == 401 and codes(me) == ["SESSION_REVOKED"]


def test_registration_can_be_closed():
    app = create_app(build_settings(registration_enabled=False))
    with TestClient(app) as closed:
        closed.portal.call(initialize_database, app)
        response = register(closed)
        assert response.status_code == 403 and codes(response) == ["REGISTRATION_DISABLED"]


def test_rate_limit_stops_a_flood_of_logins():
    app = create_app(build_settings(rate_limit_enabled=True, auth_rate_limit_per_minute=3))
    with TestClient(app) as limited:
        limited.portal.call(initialize_database, app)
        body = {"email": "nobody@example.com", "password": PASSWORD}
        statuses = [
            limited.post("/auth/login", json=body, headers=ANONYMOUS).status_code for _ in range(5)
        ]
        assert statuses == [401, 401, 401, 429, 429]


# --- Админ: бан и роли


def make_admin(client, email="boss@example.com"):
    register(client, email=email, username="boss")

    async def promote(app):
        async with app.state.db.unit_of_work() as uow:
            user = await uow.users.get_by_email(email)
            user.role = Role.ADMIN
            user.auth_version += 1  # старые токены больше не действуют, нужен вход заново

    client.portal.call(promote, client.app)
    login = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
        headers=ANONYMOUS | {"X-Client": "mobile"},
    ).json()
    return bearer(login)


def test_admin_bans_user_and_their_tokens_die(client):
    victim = register(client).json()
    admin = make_admin(client)
    victim_id = client.get("/users/me", headers=bearer(victim)).json()["id"]

    banned = client.post(f"/admin/users/{victim_id}/ban", headers=admin)
    assert banned.status_code == 200 and banned.json()["banned"] is True

    me = client.get("/users/me", headers=bearer(victim))
    assert me.status_code == 401
    login = client.post(
        "/auth/login", json={"email": "new@example.com", "password": PASSWORD}, headers=ANONYMOUS
    )
    assert login.status_code == 403 and codes(login) == ["ACCOUNT_BANNED"]

    assert client.delete(f"/admin/users/{victim_id}/ban", headers=admin).json()["banned"] is False


def test_admin_cannot_ban_self_or_change_own_role(client):
    admin = make_admin(client)
    my_id = client.get("/users/me", headers=admin).json()["id"]
    assert codes(client.post(f"/admin/users/{my_id}/ban", headers=admin)) == ["SELF_MODERATION"]
    changed = client.put(
        f"/admin/users/{my_id}/role", json={"role": "campaignManager"}, headers=admin
    )
    assert codes(changed) == ["SELF_MODERATION"]


def test_role_change_applies_to_the_next_login(client):
    user = register(client).json()
    admin = make_admin(client)
    user_id = client.get("/users/me", headers=bearer(user)).json()["id"]

    result = client.put(
        f"/admin/users/{user_id}/role", json={"role": "campaignModerator"}, headers=admin
    )
    assert result.json()["role"] == "campaignModerator"
    # Права зависят от роли, поэтому выданные токены сразу недействительны.
    assert client.get("/users/me", headers=bearer(user)).status_code == 401


def test_only_admin_reaches_admin_endpoints(client):
    manager = register(client).json()
    assert client.get("/admin/users", headers=bearer(manager)).status_code == 403
    assert client.get("/admin/users", headers=ANONYMOUS).status_code == 401
    admin = make_admin(client)
    users = client.get("/admin/users", headers=admin, params={"search": "new@"}).json()
    assert [u["email"] for u in users] == ["new@example.com"]


def test_admin_does_not_decide_campaigns(client):
    """Одобрять кампании может только модератор: у админа этого права нет."""
    admin = make_admin(client)
    response = client.post("/campaigns/101/approve", headers=admin)
    assert response.status_code == 403 and codes(response) == ["ROLE_FORBIDDEN"]


# --- Конфиг


def test_production_refuses_development_secrets():
    with pytest.raises(ValueError, match="CSRF_HMAC_KEY"):
        Settings(
            _env_file=None,
            app_stage="prod",
            database_url="postgresql+asyncpg://u:secret@h/db",
            cookie_secure=True,
        )
