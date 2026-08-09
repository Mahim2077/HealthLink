from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
from threading import Barrier, Event
import uuid

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.service import AuthenticationError, AuthService, as_utc, utc_now
from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token_for_logout,
    hash_refresh_token,
)
from app.db.session import create_database_engine


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for PostgreSQL concurrency coverage",
)
def test_concurrent_refresh_allows_exactly_one_same_row_rotation(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_id = uuid.uuid4()
    email = f"refresh-concurrency-{user_id.hex}@example.com"

    try:
        with Session(engine, expire_on_commit=False) as setup_session:
            user = User(
                id=user_id,
                email=email,
                password_hash="phase-1-concurrency-test-hash",
                first_name="Concurrent",
                last_name="Refresh",
            )
            setup_session.add(user)
            setup_session.commit()
            issued = AuthService(setup_session, test_settings).create_session(
                user.id,
                Portal.CITIZEN,
            )
            stored = setup_session.get(AuthSession, issued.session_id)
            assert stored is not None
            original_expiry = as_utc(stored.expires_at)

        barrier = Barrier(2)

        def rotate() -> tuple[str, str | None]:
            with Session(engine, expire_on_commit=False) as worker_session:
                barrier.wait(timeout=10)
                try:
                    rotated = AuthService(worker_session, test_settings).refresh_session(
                        issued.refresh_token
                    )
                    return ("rotated", rotated.refresh_token)
                except AuthenticationError:
                    return ("rejected", None)

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _index: rotate(), range(2)))

        assert [status for status, _token in outcomes].count("rotated") == 1
        assert [status for status, _token in outcomes].count("rejected") == 1
        winning_token = next(
            token for status, token in outcomes if status == "rotated"
        )
        assert winning_token is not None

        with Session(engine) as verification_session:
            stored = verification_session.get(AuthSession, issued.session_id)
            assert stored is not None
            assert stored.refresh_token_hash == hash_refresh_token(winning_token)
            assert stored.revoked_at is None
            assert stored.last_used_at is not None
            assert as_utc(stored.expires_at) == original_expiry
    finally:
        with engine.begin() as connection:
            connection.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
            connection.execute(delete(User).where(User.id == user_id))
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for PostgreSQL concurrency coverage",
)
@pytest.mark.parametrize("expired_bearer", [False, True])
def test_refresh_commit_before_cross_tab_logout_still_revokes_rotated_row(
    test_settings: Settings,
    expired_bearer: bool,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_id = uuid.uuid4()
    refresh_committed = Event()

    try:
        with Session(engine, expire_on_commit=False) as setup_session:
            user = User(
                id=user_id,
                email=f"cross-tab-logout-{user_id.hex}@example.com",
                password_hash="phase-1-cross-tab-test-hash",
                first_name="Cross Tab",
                last_name="Logout",
            )
            setup_session.add(user)
            setup_session.commit()
            first = AuthService(setup_session, test_settings).create_session(
                user.id,
                Portal.CITIZEN,
            )

        bearer_token = first.access_token
        if expired_bearer:
            bearer_token = create_access_token(
                user_id=user_id,
                portal=Portal.CITIZEN,
                session_id=first.session_id,
                settings=test_settings,
                now=utc_now() - timedelta(hours=2),
            )
        logout_claims = decode_access_token_for_logout(bearer_token, test_settings)

        def refresh_worker() -> tuple[str, int]:
            with Session(engine, expire_on_commit=False) as refresh_session:
                backend_pid = refresh_session.scalar(select(func.pg_backend_pid()))
                rotated = AuthService(
                    refresh_session,
                    test_settings,
                ).refresh_session(first.refresh_token)
                refresh_committed.set()
                return rotated.refresh_token, int(backend_pid)

        def logout_worker() -> int:
            assert refresh_committed.wait(timeout=10)
            with Session(engine) as logout_session:
                backend_pid = logout_session.scalar(select(func.pg_backend_pid()))
                AuthService(logout_session, test_settings).logout_session(
                    first.refresh_token,
                    access_claims=logout_claims,
                )
                return int(backend_pid)

        with ThreadPoolExecutor(max_workers=2) as executor:
            refresh_future = executor.submit(refresh_worker)
            logout_future = executor.submit(logout_worker)
            rotated_refresh_token, refresh_pid = refresh_future.result(timeout=15)
            logout_pid = logout_future.result(timeout=15)

        assert refresh_pid != logout_pid
        with Session(engine) as verification_session:
            stored = verification_session.get(AuthSession, first.session_id)
            assert stored is not None
            assert stored.revoked_at is not None
            with pytest.raises(AuthenticationError):
                AuthService(
                    verification_session,
                    test_settings,
                ).refresh_session(rotated_refresh_token)
    finally:
        with engine.begin() as connection:
            connection.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
            connection.execute(delete(User).where(User.id == user_id))
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for PostgreSQL constraint coverage",
)
def test_postgresql_auth_constraints_foreign_key_defaults_and_timezones() -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_id = uuid.uuid4()
    email = f"postgres-constraints-{user_id.hex}@example.com"
    refresh_hash = f"refresh-{user_id.hex}"

    try:
        with Session(engine, expire_on_commit=False) as session:
            user = User(
                id=user_id,
                email=email,
                password_hash="phase-1-postgresql-test-hash",
                first_name="PostgreSQL",
                last_name="Constraint",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            assert user.is_active is True
            assert user.created_at.tzinfo is not None
            assert user.updated_at.tzinfo is not None

            auth_session = AuthSession(
                user_id=user.id,
                portal=Portal.CITIZEN.value,
                refresh_token_hash=refresh_hash,
                expires_at=user.created_at,
            )
            session.add(auth_session)
            session.commit()
            session.refresh(auth_session)
            assert auth_session.created_at.tzinfo is not None

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    User(
                        email=email,
                        password_hash="duplicate-email",
                        first_name="Duplicate",
                        last_name="Email",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    AuthSession(
                        user_id=user_id,
                        portal=Portal.ADMIN.value,
                        refresh_token_hash=refresh_hash,
                        expires_at=user.created_at,
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    AuthSession(
                        user_id=user_id,
                        portal="UNKNOWN",
                        refresh_token_hash=f"invalid-portal-{user_id.hex}",
                        expires_at=user.created_at,
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    AuthSession(
                        user_id=uuid.uuid4(),
                        portal=Portal.CITIZEN.value,
                        refresh_token_hash=f"invalid-user-{user_id.hex}",
                        expires_at=user.created_at,
                    )
                )
                session.commit()
    finally:
        with engine.begin() as connection:
            connection.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
            connection.execute(delete(User).where(User.id == user_id))
        engine.dispose()
