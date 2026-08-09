from collections.abc import Callable
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.service import AuthenticationError, AuthService, as_utc, utc_now
from app.core.config import Settings
from app.core.security import decode_access_token, hash_refresh_token


def test_create_session_stores_only_refresh_hash_and_issues_access_token(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)

    tokens = service.create_session(user.id, Portal.CITIZEN)
    stored_session = db_session.get(AuthSession, tokens.session_id)

    assert stored_session is not None
    assert stored_session.refresh_token_hash == hash_refresh_token(tokens.refresh_token)
    assert tokens.refresh_token not in stored_session.refresh_token_hash
    claims = decode_access_token(tokens.access_token, test_settings)
    assert claims.sub == user.id
    assert claims.sid == stored_session.id
    assert claims.portal is Portal.CITIZEN


def test_refresh_rotates_hash_in_same_locked_row_and_preserves_expiry(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    issued = service.create_session(user.id, Portal.ADMIN)
    stored_session = db_session.get(AuthSession, issued.session_id)
    assert stored_session is not None
    original_expiry = as_utc(stored_session.expires_at)
    refresh_time = utc_now() + timedelta(seconds=1)

    rotated = service.refresh_session(issued.refresh_token, now=refresh_time)
    db_session.refresh(stored_session)

    assert rotated.session_id == issued.session_id
    assert rotated.refresh_token != issued.refresh_token
    assert stored_session.refresh_token_hash == hash_refresh_token(rotated.refresh_token)
    assert stored_session.last_used_at is not None
    assert stored_session.revoked_at is None
    assert rotated.portal is Portal.ADMIN
    assert as_utc(stored_session.expires_at) == original_expiry
    assert as_utc(rotated.refresh_token_expires_at) == original_expiry


def test_rotated_refresh_token_cannot_be_replayed(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    issued = service.create_session(user.id, Portal.CITIZEN)
    rotated = service.refresh_session(issued.refresh_token)

    with pytest.raises(AuthenticationError):
        service.refresh_session(issued.refresh_token)

    assert service.refresh_session(rotated.refresh_token).session_id == issued.session_id


def test_unknown_and_revoked_refresh_tokens_are_rejected_without_side_effects(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    issued = service.create_session(user.id, Portal.CITIZEN)

    with pytest.raises(AuthenticationError):
        service.refresh_session("unknown-refresh-token")

    service.logout_by_refresh_token(issued.refresh_token)
    with pytest.raises(AuthenticationError):
        service.refresh_session(issued.refresh_token)


def test_expired_refresh_token_is_revoked_and_rejected(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    now = utc_now()
    issued = service.create_session(
        user.id,
        Portal.CITIZEN,
        now=now - timedelta(days=test_settings.refresh_token_expire_days + 1),
    )

    with pytest.raises(AuthenticationError):
        service.refresh_session(issued.refresh_token, now=now)

    stored_session = db_session.get(AuthSession, issued.session_id)
    assert stored_session is not None
    assert stored_session.revoked_at is not None


def test_inactive_user_cannot_receive_or_refresh_session(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    inactive_user = user_factory(is_active=False)

    with pytest.raises(AuthenticationError):
        AuthService(db_session, test_settings).create_session(
            inactive_user.id,
            Portal.CITIZEN,
        )

    active_user = user_factory()
    service = AuthService(db_session, test_settings)
    issued = service.create_session(active_user.id, Portal.CITIZEN)
    active_user.is_active = False
    db_session.commit()

    with pytest.raises(AuthenticationError):
        service.refresh_session(issued.refresh_token)


def test_cookie_logout_is_idempotent_and_logout_all_revokes_every_session(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    first = service.create_session(user.id, Portal.CITIZEN)
    second = service.create_session(user.id, Portal.ADMIN)

    service.logout_by_refresh_token(first.refresh_token)
    service.logout_by_refresh_token(first.refresh_token)
    service.logout_by_refresh_token("unknown-refresh-token")

    first_session = db_session.get(AuthSession, first.session_id)
    second_session = db_session.get(AuthSession, second.session_id)
    assert first_session is not None and first_session.revoked_at is not None
    assert second_session is not None and second_session.revoked_at is None

    assert service.logout_all(user.id) == 1
    db_session.refresh(second_session)
    assert second_session.revoked_at is not None
    assert len(db_session.scalars(select(AuthSession)).all()) == 2
