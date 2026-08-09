from collections.abc import Callable
from datetime import timedelta
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.service import AuthService, utc_now
from app.core.config import Settings
from app.core.security import create_access_token


PROTECTED_ENDPOINT = "/api/v1/auth/logout-all"


def _authorization(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_current_auth_rejects_missing_session(
    client: TestClient,
    test_settings: Settings,
) -> None:
    token = create_access_token(
        user_id=uuid.uuid4(),
        portal=Portal.CITIZEN,
        session_id=uuid.uuid4(),
        settings=test_settings,
    )

    assert client.post(PROTECTED_ENDPOINT, headers=_authorization(token)).status_code == 401


def test_current_auth_rejects_revoked_session(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    service = AuthService(db_session, test_settings)
    issued = service.create_session(user.id, Portal.CITIZEN)
    service.logout_by_refresh_token(issued.refresh_token)

    response = client.post(
        PROTECTED_ENDPOINT,
        headers=_authorization(issued.access_token),
    )

    assert response.status_code == 401


def test_current_auth_rejects_expired_refresh_session_even_with_live_access_token(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    issued = AuthService(db_session, test_settings).create_session(
        user.id,
        Portal.CITIZEN,
    )
    auth_session = db_session.get(AuthSession, issued.session_id)
    assert auth_session is not None
    auth_session.expires_at = utc_now() - timedelta(seconds=1)
    db_session.commit()

    response = client.post(
        PROTECTED_ENDPOINT,
        headers=_authorization(issued.access_token),
    )

    assert response.status_code == 401


def test_current_auth_rejects_user_mismatched_session(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    session_owner = user_factory()
    other_user = user_factory()
    issued = AuthService(db_session, test_settings).create_session(
        session_owner.id,
        Portal.CITIZEN,
    )
    mismatched_token = create_access_token(
        user_id=other_user.id,
        portal=Portal.CITIZEN,
        session_id=issued.session_id,
        settings=test_settings,
    )

    response = client.post(
        PROTECTED_ENDPOINT,
        headers=_authorization(mismatched_token),
    )

    assert response.status_code == 401


def test_current_auth_rejects_portal_mismatched_session(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    issued = AuthService(db_session, test_settings).create_session(
        user.id,
        Portal.CITIZEN,
    )
    mismatched_token = create_access_token(
        user_id=user.id,
        portal=Portal.ADMIN,
        session_id=issued.session_id,
        settings=test_settings,
    )

    response = client.post(
        PROTECTED_ENDPOINT,
        headers=_authorization(mismatched_token),
    )

    assert response.status_code == 401


def test_current_auth_rejects_inactive_user(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    user = user_factory()
    issued = AuthService(db_session, test_settings).create_session(
        user.id,
        Portal.CITIZEN,
    )
    user.is_active = False
    db_session.commit()

    response = client.post(
        PROTECTED_ENDPOINT,
        headers=_authorization(issued.access_token),
    )

    assert response.status_code == 401


def test_current_auth_defensively_rejects_session_whose_user_is_missing(
    client: TestClient,
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    # SQLite's test connection does not enforce foreign keys by default, which
    # lets this exercise the defensive lookup. PostgreSQL prevents this state.
    user = user_factory()
    issued = AuthService(db_session, test_settings).create_session(
        user.id,
        Portal.CITIZEN,
    )
    db_session.execute(delete(User).where(User.id == user.id))
    db_session.commit()
    db_session.expunge_all()

    response = client.post(
        PROTECTED_ENDPOINT,
        headers=_authorization(issued.access_token),
    )

    assert response.status_code == 401
