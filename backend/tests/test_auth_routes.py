from collections.abc import Callable
from datetime import timedelta
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, require_portal
from app.auth.models import AuthSession, User
from app.auth.service import AuthenticationError, AuthService, as_utc, utc_now
from app.core.config import Settings
from app.core.security import (
    REFRESH_TOKEN_COOKIE_NAME,
    create_access_token,
    decode_access_token,
)


AUTH_COOKIE_PATH = "/api/v1/auth"


def _issue_tokens(
    db_session: Session,
    settings: Settings,
    user: User,
    portal: Portal = Portal.CITIZEN,
):
    return AuthService(db_session, settings).create_session(user.id, portal)


def _set_refresh_cookie(client: TestClient, refresh_token: str) -> None:
    client.cookies.set(
        REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        domain="testserver.local",
        path=AUTH_COOKIE_PATH,
    )


def test_refresh_endpoint_rotates_cookie_without_exposing_it_in_json(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    issued = _issue_tokens(db_session, test_settings, user)
    original_session = db_session.get(AuthSession, issued.session_id)
    assert original_session is not None
    original_expiry = original_session.expires_at
    _set_refresh_cookie(client, issued.refresh_token)

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    body = response.json()
    assert "refresh_token" not in body
    assert body["portal"] == "CITIZEN"
    claims = decode_access_token(body["access_token"], test_settings)
    assert claims.sid == issued.session_id
    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Max-Age=" in set_cookie
    parsed_cookie = SimpleCookie()
    parsed_cookie.load(set_cookie)
    refresh_cookie = parsed_cookie[REFRESH_TOKEN_COOKIE_NAME]
    cookie_max_age = int(refresh_cookie["max-age"])
    expected_remaining = int((as_utc(original_expiry) - utc_now()).total_seconds())
    assert abs(cookie_max_age - expected_remaining) <= 2
    cookie_expiry = parsedate_to_datetime(refresh_cookie["expires"])
    assert abs((cookie_expiry - as_utc(original_expiry)).total_seconds()) <= 1
    db_session.refresh(original_session)
    assert original_session.expires_at == original_expiry


def test_refresh_requires_cookie(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_logout_is_cookie_based_idempotent_and_always_clears_cookie(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    missing_response = client.post("/api/v1/auth/logout")
    assert missing_response.status_code == 204
    assert missing_response.content == b""
    missing_cookie = missing_response.headers["set-cookie"]
    assert "Max-Age=0" in missing_cookie
    assert "Path=/api/v1/auth" in missing_cookie
    assert "HttpOnly" in missing_cookie
    assert "SameSite=lax" in missing_cookie

    user = user_factory()
    issued = _issue_tokens(db_session, test_settings, user)
    _set_refresh_cookie(client, issued.refresh_token)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    stored_session = db_session.get(AuthSession, issued.session_id)
    assert stored_session is not None and stored_session.revoked_at is not None

    _set_refresh_cookie(client, "unknown-token")
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_logout_valid_bearer_revokes_same_session_after_cookie_rotation_race(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    first = service.create_session(user.id, Portal.CITIZEN)
    rotated = service.refresh_session(first.refresh_token)
    _set_refresh_cookie(client, first.refresh_token)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {first.access_token}"},
    )

    assert response.status_code == 204
    stored_session = db_session.get(AuthSession, first.session_id)
    assert stored_session is not None and stored_session.revoked_at is not None
    with pytest.raises(AuthenticationError):
        service.refresh_session(rotated.refresh_token)


def test_logout_expired_bearer_can_only_revoke_its_own_rotated_session(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    first = service.create_session(user.id, Portal.CITIZEN)
    rotated = service.refresh_session(first.refresh_token)
    expired_access_token = create_access_token(
        user_id=user.id,
        portal=Portal.CITIZEN,
        session_id=first.session_id,
        settings=test_settings,
        now=utc_now() - timedelta(hours=2),
    )
    _set_refresh_cookie(client, first.refresh_token)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )

    assert response.status_code == 204
    stored_session = db_session.get(AuthSession, first.session_id)
    assert stored_session is not None and stored_session.revoked_at is not None
    with pytest.raises(AuthenticationError):
        service.refresh_session(rotated.refresh_token)


def test_logout_malformed_optional_bearer_falls_back_to_cookie(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    issued = _issue_tokens(db_session, test_settings, user)
    _set_refresh_cookie(client, issued.refresh_token)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer malformed.jwt.value"},
    )

    assert response.status_code == 204
    stored_session = db_session.get(AuthSession, issued.session_id)
    assert stored_session is not None and stored_session.revoked_at is not None


def test_logout_signed_bearer_and_cookie_each_revoke_their_represented_session(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    bearer_user = user_factory()
    cookie_user = user_factory()
    bearer_session = _issue_tokens(db_session, test_settings, bearer_user)
    cookie_session = _issue_tokens(db_session, test_settings, cookie_user)
    _set_refresh_cookie(client, cookie_session.refresh_token)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {bearer_session.access_token}"},
    )

    assert response.status_code == 204
    bearer_stored = db_session.get(AuthSession, bearer_session.session_id)
    cookie_stored = db_session.get(AuthSession, cookie_session.session_id)
    assert bearer_stored is not None and bearer_stored.revoked_at is not None
    assert cookie_stored is not None and cookie_stored.revoked_at is not None


def test_logout_signed_claims_cannot_revoke_a_session_owned_by_another_user(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    token_user = user_factory()
    session_owner = user_factory()
    protected_session = _issue_tokens(db_session, test_settings, session_owner)
    mismatched_token = create_access_token(
        user_id=token_user.id,
        portal=Portal.CITIZEN,
        session_id=protected_session.session_id,
        settings=test_settings,
    )

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {mismatched_token}"},
    )

    assert response.status_code == 204
    stored_session = db_session.get(AuthSession, protected_session.session_id)
    assert stored_session is not None and stored_session.revoked_at is None


def test_logout_after_rotation_revokes_the_cookie_that_won_rotation(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    issued = _issue_tokens(db_session, test_settings, user)
    _set_refresh_cookie(client, issued.refresh_token)

    refresh_response = client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    rotated_refresh_token = client.cookies.get(
        REFRESH_TOKEN_COOKIE_NAME,
        domain="testserver.local",
        path=AUTH_COOKIE_PATH,
    )
    assert rotated_refresh_token is not None
    assert rotated_refresh_token != issued.refresh_token

    logout_response = client.post("/api/v1/auth/logout")

    assert logout_response.status_code == 204
    stored_session = db_session.get(AuthSession, issued.session_id)
    assert stored_session is not None
    db_session.refresh(stored_session)
    assert stored_session.revoked_at is not None

    # Even if a stale client replays the post-rotation cookie, the revoked
    # session cannot mint another access token.
    _set_refresh_cookie(client, rotated_refresh_token)
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_all_requires_bearer_and_revokes_every_user_session(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    assert client.post("/api/v1/auth/logout-all").status_code == 401

    user = user_factory()
    first = _issue_tokens(db_session, test_settings, user, Portal.CITIZEN)
    second = _issue_tokens(db_session, test_settings, user, Portal.ADMIN)
    other_user = user_factory()
    other_session_tokens = _issue_tokens(
        db_session,
        test_settings,
        other_user,
        Portal.CITIZEN,
    )

    response = client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {first.access_token}"},
    )

    assert response.status_code == 204
    assert response.content == b""
    first_session = db_session.get(AuthSession, first.session_id)
    second_session = db_session.get(AuthSession, second.session_id)
    other_session = db_session.get(AuthSession, other_session_tokens.session_id)
    db_session.refresh(first_session)
    db_session.refresh(second_session)
    db_session.refresh(other_session)
    assert first_session.revoked_at is not None
    assert second_session.revoked_at is not None
    assert other_session.revoked_at is None
    assert (
        client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {first.access_token}"},
        ).status_code
        == 401
    )


def test_require_portal_rejects_wrong_context_and_allows_matching_context(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    @client.app.get("/_test/admin-only")
    def admin_only(
        _context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
    ) -> dict[str, bool]:
        return {"allowed": True}

    user = user_factory()
    citizen = _issue_tokens(db_session, test_settings, user, Portal.CITIZEN)
    admin = _issue_tokens(db_session, test_settings, user, Portal.ADMIN)

    denied = client.get(
        "/_test/admin-only",
        headers={"Authorization": f"Bearer {citizen.access_token}"},
    )
    allowed = client.get(
        "/_test/admin-only",
        headers={"Authorization": f"Bearer {admin.access_token}"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json() == {"allowed": True}
