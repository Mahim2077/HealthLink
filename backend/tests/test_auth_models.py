from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.service import utc_now


def test_user_email_is_unique(db_session: Session, user_factory) -> None:
    user_factory(email="unique@example.com")
    duplicate = User(
        email="unique@example.com",
        password_hash="hash",
        first_name="Duplicate",
        last_name="User",
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_refresh_hash_is_unique(db_session: Session, user_factory) -> None:
    user = user_factory()
    expiry = utc_now() + timedelta(days=1)
    db_session.add_all(
        [
            AuthSession(
                user_id=user.id,
                portal=Portal.CITIZEN.value,
                refresh_token_hash="same-hash",
                expires_at=expiry,
            ),
            AuthSession(
                user_id=user.id,
                portal=Portal.ADMIN.value,
                refresh_token_hash="same-hash",
                expires_at=expiry,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_portal_constraint_rejects_unknown_value(
    db_session: Session,
    user_factory,
) -> None:
    user = user_factory()
    db_session.add(
        AuthSession(
            user_id=user.id,
            portal="UNKNOWN",
            refresh_token_hash="unique-hash",
            expires_at=utc_now() + timedelta(days=1),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
