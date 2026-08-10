"""PostgreSQL-specific Phase 8 tests for admin citizen identity support.

Covers database-level enforcement that the SQLite tests cannot verify:

* Unique constraint on `user_national_identifiers.nid_number`.
* Unique constraint on `citizen_identifiers.birth_certificate_number`.
* Foreign key from `admin_action_logs.admin_user_id` to `users.id`.
* Live `POST /api/v1/admin/citizens/{user_id}/identity/correct` writes the
  audit log row with the corrected resource pointer.
* Service-layer conflict detection against an existing citizen's NID.
"""

from __future__ import annotations

import os
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.admins.identity_service import (
    CitizenIdentityConflictError,
    CitizenIdentitySupportService,
)
from app.admins.models import AdminAccount, AdminActionLog
from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.service import AuthService
from app.citizens.constants import CitizenRegistrationMethod
from app.citizens.models import (
    CitizenIdentifier,
    CitizenProfile,
    UserNationalIdentifier,
)
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import create_database_engine, get_db
from app.main import create_app


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for admin identity support PostgreSQL coverage",
)


def _make_admin(session: Session, suffix: str) -> User:
    user = User(
        email=f"phase8-admin-{suffix}@example.com",
        password_hash=hash_password("SudoAdminPass123!"),
        first_name="Phase",
        last_name="Eight",
    )
    session.add(user)
    session.flush()
    session.add(AdminAccount(user_id=user.id, is_super_admin=True, is_active=True))
    session.flush()
    return user


def _cleanup(engine, *, admin_user_id=None, citizen_user_ids=None, nid_numbers=None, bcn_numbers=None):
    """Delete all FK dependents before deleting users."""
    with engine.begin() as connection:
        if admin_user_id is not None:
            connection.execute(
                delete(AdminActionLog).where(AdminActionLog.admin_user_id == admin_user_id)
            )
            connection.execute(
                delete(AdminAccount).where(AdminAccount.user_id == admin_user_id)
            )
            connection.execute(
                AuthSession.__table__.delete().where(AuthSession.user_id == admin_user_id)
            )
        if citizen_user_ids:
            connection.execute(
                AuthSession.__table__.delete().where(AuthSession.user_id.in_(citizen_user_ids))
            )
            connection.execute(
                delete(CitizenIdentifier).where(CitizenIdentifier.user_id.in_(citizen_user_ids))
            )
            connection.execute(
                delete(CitizenProfile).where(CitizenProfile.user_id.in_(citizen_user_ids))
            )
            connection.execute(
                delete(UserNationalIdentifier).where(
                    UserNationalIdentifier.user_id.in_(citizen_user_ids)
                )
            )
        if nid_numbers:
            # Unlink citizen_identifiers.national_identifier_id before deleting
            # user_national_identifiers (FK with ON DELETE RESTRICT). Target only
            # the identifiers that reference rows we're about to delete.
            target_ni_ids = connection.execute(
                select(UserNationalIdentifier.id).where(
                    UserNationalIdentifier.nid_number.in_(nid_numbers)
                )
            ).scalars().all()
            if target_ni_ids:
                connection.execute(
                    update(CitizenIdentifier)
                    .where(CitizenIdentifier.national_identifier_id.in_(target_ni_ids))
                    .values(national_identifier_id=None)
                )
            connection.execute(
                delete(UserNationalIdentifier).where(
                    UserNationalIdentifier.nid_number.in_(nid_numbers)
                )
            )
        if bcn_numbers:
            connection.execute(
                delete(CitizenIdentifier).where(
                    CitizenIdentifier.birth_certificate_number.in_(bcn_numbers)
                )
            )
        if admin_user_id is not None:
            connection.execute(delete(User).where(User.id == admin_user_id))
        if citizen_user_ids:
            connection.execute(delete(User).where(User.id.in_(citizen_user_ids)))


def _make_citizen(session: Session, suffix: str) -> tuple[User, UserNationalIdentifier, CitizenIdentifier]:
    from datetime import date

    user = User(
        email=f"phase8-citizen-{suffix}@example.com",
        password_hash=hash_password("CitizenPass123!"),
        first_name="Live",
        last_name="Citizen",
    )
    session.add(user)
    session.flush()
    national = UserNationalIdentifier(user_id=user.id, nid_number=f"P8NID{suffix}")
    session.add(national)
    session.flush()
    profile = CitizenProfile(
        user_id=user.id,
        date_of_birth=date(1990, 1, 1),
        gender="unspecified",
    )
    session.add(profile)
    session.flush()
    identity = CitizenIdentifier(
        user_id=user.id,
        registered_with=CitizenRegistrationMethod.NID.value,
        national_identifier_id=national.id,
        birth_certificate_number=f"P8BCN{suffix}",
    )
    session.add(identity)
    session.flush()
    return user, national, identity


def test_postgresql_unique_constraint_on_national_identifier() -> None:
    """`user_national_identifiers.nid_number` is unique at the database level."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex[:12]
    try:
        with Session(engine, expire_on_commit=False) as session:
            _make_citizen(session, suffix)
            session.commit()
        with Session(engine, expire_on_commit=False) as session:
            other = User(
                email=f"phase8-other-{suffix}@example.com",
                password_hash=hash_password("OtherPass123!"),
                first_name="Other",
                last_name="Citizen",
            )
            session.add(other)
            session.flush()
            session.add(
                UserNationalIdentifier(user_id=other.id, nid_number=f"P8NID{suffix}")
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        _cleanup(engine, nid_numbers=[f"P8NID{suffix}"])
        engine.dispose()


def test_postgresql_unique_constraint_on_birth_certificate() -> None:
    """`citizen_identifiers.birth_certificate_number` is unique at the database level."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex[:12]
    try:
        with Session(engine, expire_on_commit=False) as session:
            _make_citizen(session, suffix)
            session.commit()
        with Session(engine, expire_on_commit=False) as session:
            other = User(
                email=f"phase8-other-{suffix}@example.com",
                password_hash=hash_password("OtherPass123!"),
                first_name="Other",
                last_name="Citizen",
            )
            session.add(other)
            session.flush()
            session.add(
                CitizenIdentifier(
                    user_id=other.id,
                    registered_with=CitizenRegistrationMethod.NID.value,
                    birth_certificate_number=f"P8BCN{suffix}",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        _cleanup(engine, bcn_numbers=[f"P8BCN{suffix}"])
        engine.dispose()


def test_postgresql_admin_action_log_foreign_key_to_user() -> None:
    """`admin_action_logs.admin_user_id` FK rejects orphan admin_user_id values."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    try:
        with Session(engine, expire_on_commit=False) as session:
            session.add(
                AdminActionLog(
                    admin_user_id=uuid.uuid4(),
                    action_type="PHASE8_PROBE",
                    target_user_id=None,
                    target_resource_type=None,
                    target_resource_id=None,
                    reason="probe",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        engine.dispose()


def test_postgresql_live_correction_writes_audit_log(test_settings: Settings) -> None:
    """End-to-end: login admin, correct NID via HTTP, verify audit log row."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    app = create_app(test_settings)

    def postgres_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = postgres_db

    suffix = uuid.uuid4().hex[:12]
    admin_user_id: uuid.UUID | None = None
    citizen_user_id: uuid.UUID | None = None
    new_nid = f"P8NIDNEW{suffix}"
    token: str | None = None
    try:
        with Session(engine, expire_on_commit=False) as session:
            admin_user = _make_admin(session, suffix)
            citizen, _, _ = _make_citizen(session, suffix)
            admin_user_id = admin_user.id
            citizen_user_id = citizen.id
            issued = AuthService(session, test_settings).create_session(
                admin_user.id, Portal.ADMIN
            )
            token = issued.access_token
            session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/admin/citizen-identities/{citizen_user_id}/correct",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "correction_type": "NID",
                    "new_value": new_nid,
                    "reason": "Phase 8 PG live probe",
                },
            )
            assert response.status_code == 200, response.text
            payload = response.json()
            assert payload["new_value"] == new_nid
            audit_log_id = payload["audit_log_id"]
            assert audit_log_id

        with Session(engine, expire_on_commit=False) as session:
            audit = session.scalar(
                select(AdminActionLog).where(AdminActionLog.id == uuid.UUID(audit_log_id))
            )
            assert audit is not None
            assert audit.action_type == "CITIZEN_IDENTITY_CORRECT_NID"
            assert audit.target_user_id == citizen_user_id
            assert audit.admin_user_id == admin_user_id
            assert audit.reason == "Phase 8 PG live probe"
            assert audit.target_resource_type == "USER_NATIONAL_IDENTIFIER"
            assert audit.target_resource_id is not None
    finally:
        _cleanup(
            engine,
            admin_user_id=admin_user_id,
            citizen_user_ids=[citizen_user_id] if citizen_user_id else None,
            nid_numbers=[new_nid],
            bcn_numbers=[f"P8BCN{suffix}"],
        )
        engine.dispose()


def test_postgresql_correction_conflict_raises_service_error() -> None:
    """Service-layer conflict detection rejects a duplicate NID correction."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex[:12]
    other_suffix = f"other{suffix}"
    citizen_user_id: uuid.UUID | None = None
    other_citizen_user_id: uuid.UUID | None = None
    try:
        with Session(engine, expire_on_commit=False) as session:
            citizen, _, _ = _make_citizen(session, suffix)
            other_citizen, _, _ = _make_citizen(session, other_suffix)
            session.commit()
            citizen_user_id = citizen.id
            other_citizen_user_id = other_citizen.id

        from app.admins.identity_schemas import CitizenIdentityCorrectionRequest

        with Session(engine, expire_on_commit=False) as session:
            service = CitizenIdentitySupportService(session)
            request = CitizenIdentityCorrectionRequest(
                correction_type="NID",
                new_value=f"P8NID{suffix}",
                reason="should conflict",
            )
            with pytest.raises(CitizenIdentityConflictError):
                service.correct(
                    other_citizen_user_id,
                    request,
                    admin_user_id=uuid.uuid4(),
                )
    finally:
        _cleanup(
            engine,
            citizen_user_ids=[citizen_user_id, other_citizen_user_id],
            nid_numbers=[f"P8NID{suffix}", f"P8NID{other_suffix}"],
            bcn_numbers=[f"P8BCN{suffix}", f"P8BCN{other_suffix}"],
        )
        engine.dispose()
