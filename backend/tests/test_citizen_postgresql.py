from concurrent.futures import ThreadPoolExecutor
from datetime import date
import os
from threading import Barrier
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth.models import AuthSession, User
from app.citizens.models import (
    CitizenIdentifier,
    CitizenProfile,
    UserNationalIdentifier,
)
from app.citizens.schemas import CitizenAddNidRequest, CitizenRegistrationRequest
from app.citizens.service import (
    CitizenConflictError,
    CitizenIdentityUpgradeError,
    CitizenService,
)
from app.core.config import Settings
from app.core.security import REFRESH_TOKEN_COOKIE_NAME, hash_password
from app.db.session import create_database_engine, get_db
from app.main import create_app


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


def _registration(email: str, nid_number: str) -> CitizenRegistrationRequest:
    return CitizenRegistrationRequest(
        email=email,
        password="StrongPassword123!",
        first_name="PostgreSQL",
        last_name="Citizen",
        date_of_birth=date(1990, 1, 1),
        gender="OTHER",
        blood_group=None,
        address=None,
        nid_number=nid_number,
        birth_certificate_number=None,
    )


def _nid(value: uuid.UUID, prefix: str = "") -> str:
    """Return a unique NID that remains within the schema's 32-char limit."""

    return f"{prefix}{value.hex}"[:32]


def _bcn(value: uuid.UUID, prefix: str = "BCN-") -> str:
    return f"{prefix}{value.hex}"[:64]


def _delete_users(engine, user_ids: list[uuid.UUID]) -> None:
    if not user_ids:
        return
    with engine.begin() as connection:
        connection.execute(
            delete(CitizenIdentifier).where(CitizenIdentifier.user_id.in_(user_ids))
        )
        connection.execute(
            delete(CitizenProfile).where(CitizenProfile.user_id.in_(user_ids))
        )
        connection.execute(
            delete(UserNationalIdentifier).where(
                UserNationalIdentifier.user_id.in_(user_ids)
            )
        )
        connection.execute(
            delete(AuthSession).where(AuthSession.user_id.in_(user_ids))
        )
        connection.execute(delete(User).where(User.id.in_(user_ids)))


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for citizen PostgreSQL coverage",
)
def test_postgresql_citizen_constraints_defaults_and_upgrade_compatible_or_check() -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_ids = [uuid.uuid4() for _ in range(5)]

    try:
        with Session(engine, expire_on_commit=False) as session:
            users = [
                User(
                    id=user_id,
                    email=f"citizen-constraint-{user_id.hex}@example.com",
                    password_hash="postgresql-constraint-hash",
                    first_name="Constraint",
                    last_name="Citizen",
                )
                for user_id in user_ids
            ]
            session.add_all(users)
            session.commit()

            national_identifier = UserNationalIdentifier(
                user_id=user_ids[0],
                nid_number=_nid(user_ids[0]),
            )
            profile = CitizenProfile(
                user_id=user_ids[0],
                date_of_birth=date(1990, 1, 1),
                gender="OTHER",
            )
            session.add_all([national_identifier, profile])
            session.flush()
            identity = CitizenIdentifier(
                user_id=user_ids[0],
                national_identifier_id=national_identifier.id,
                registered_with="NID",
            )
            session.add(identity)
            session.commit()
            session.refresh(national_identifier)
            session.refresh(profile)
            session.refresh(identity)
            assert national_identifier.created_at.tzinfo is not None
            assert profile.created_at.tzinfo is not None
            assert identity.created_at.tzinfo is not None

            # The database intentionally permits both after the later BCN→NID
            # upgrade; Phase 2 registration enforces XOR in service/schema.
            upgraded_nid = UserNationalIdentifier(
                user_id=user_ids[1],
                nid_number=_nid(user_ids[1]),
            )
            session.add(upgraded_nid)
            session.flush()
            both_identity = CitizenIdentifier(
                user_id=user_ids[1],
                national_identifier_id=upgraded_nid.id,
                birth_certificate_number=_bcn(user_ids[1]),
                registered_with="BCN",
            )
            session.add(both_identity)
            session.commit()

            bcn_identity = CitizenIdentifier(
                user_id=user_ids[2],
                birth_certificate_number=_bcn(user_ids[2]),
                registered_with="BCN",
            )
            session.add(bcn_identity)
            session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    UserNationalIdentifier(
                        user_id=user_ids[3],
                        nid_number=_nid(user_ids[0]),
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    UserNationalIdentifier(
                        user_id=user_ids[0],
                        nid_number=_nid(user_ids[3]),
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    UserNationalIdentifier(
                        user_id=uuid.uuid4(),
                        nid_number=_nid(uuid.uuid4()),
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenIdentifier(
                        user_id=user_ids[3],
                        birth_certificate_number=_bcn(user_ids[2]),
                        registered_with="BCN",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenIdentifier(
                        user_id=user_ids[0],
                        birth_certificate_number=_bcn(uuid.uuid4()),
                        registered_with="BCN",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenIdentifier(
                        user_id=user_ids[3],
                        national_identifier_id=national_identifier.id,
                        registered_with="NID",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenIdentifier(
                        user_id=user_ids[3],
                        registered_with="NID",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenIdentifier(
                        user_id=uuid.uuid4(),
                        birth_certificate_number=_bcn(uuid.uuid4()),
                        registered_with="BCN",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenIdentifier(
                        user_id=user_ids[3],
                        birth_certificate_number=_bcn(user_ids[3]),
                        registered_with="UNKNOWN",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenIdentifier(
                        user_id=user_ids[3],
                        national_identifier_id=uuid.uuid4(),
                        registered_with="NID",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenProfile(
                        user_id=uuid.uuid4(),
                        date_of_birth=date(1990, 1, 1),
                        gender="OTHER",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    CitizenProfile(
                        user_id=user_ids[0],
                        date_of_birth=date(1991, 1, 1),
                        gender="OTHER",
                    )
                )
                session.commit()
    finally:
        _delete_users(engine, user_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for citizen PostgreSQL coverage",
)
def test_concurrent_same_nid_registration_has_exactly_one_winner(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex
    shared_nid = f"R{suffix}"[:32]
    emails = [f"race-a-{suffix}@example.com", f"race-b-{suffix}@example.com"]
    barrier = Barrier(2)

    def register(email: str) -> tuple[str, uuid.UUID | None]:
        with Session(engine, expire_on_commit=False) as session:
            barrier.wait(timeout=10)
            try:
                result = CitizenService(session, test_settings).register(
                    _registration(email, shared_nid)
                )
                return "created", result.user.id
            except CitizenConflictError:
                return "conflict", None

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(register, emails))

        assert [status for status, _user_id in outcomes].count("created") == 1
        assert [status for status, _user_id in outcomes].count("conflict") == 1
        with Session(engine) as session:
            stored = session.scalars(
                select(UserNationalIdentifier).where(
                    UserNationalIdentifier.nid_number == shared_nid
                )
            ).all()
            assert len(stored) == 1
            created_users = session.scalars(
                select(User).where(User.email.in_(emails))
            ).all()
            assert len(created_users) == 1
            created_user_id = created_users[0].id
            assert session.scalar(
                select(CitizenProfile).where(
                    CitizenProfile.user_id == created_user_id
                )
            ) is not None
            assert session.scalar(
                select(CitizenIdentifier).where(
                    CitizenIdentifier.user_id == created_user_id
                )
            ) is not None
    finally:
        with Session(engine) as session:
            remaining_ids = list(
                session.scalars(select(User.id).where(User.email.in_(emails))).all()
            )
        _delete_users(engine, remaining_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for citizen PostgreSQL coverage",
)
def test_citizen_register_login_and_self_reads_against_postgresql(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex
    email = f"citizen-e2e-{suffix}@example.com"
    nid_number = f"E{suffix}"[:32]
    application = create_app(test_settings)

    def postgres_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    application.dependency_overrides[get_db] = postgres_db
    user_ids: list[uuid.UUID] = []
    try:
        with TestClient(application) as client:
            registration = client.post(
                "/api/v1/auth/citizen/register",
                json={
                    "email": email,
                    "password": "StrongPassword123!",
                    "first_name": "Live",
                    "last_name": "PostgreSQL",
                    "date_of_birth": "1990-01-01",
                    "gender": "OTHER",
                    "nid_number": nid_number,
                },
            )
            assert registration.status_code == 201
            user_ids.append(uuid.UUID(registration.json()["user_id"]))

            login = client.post(
                "/api/v1/auth/citizen/login",
                json={"email": email, "password": "StrongPassword123!"},
            )
            assert login.status_code == 200
            login_body = login.json()
            assert set(login_body) == {
                "access_token",
                "token_type",
                "expires_in",
                "portal",
            }
            assert "refresh_token" not in login_body
            set_cookie = login.headers["set-cookie"]
            assert f"{REFRESH_TOKEN_COOKIE_NAME}=" in set_cookie
            assert "HttpOnly" in set_cookie
            assert "Path=/api/v1/auth" in set_cookie
            assert "SameSite=lax" in set_cookie
            assert "Max-Age=" in set_cookie
            assert "expires=" in set_cookie.lower()
            assert "Secure" not in set_cookie
            headers = {
                "Authorization": f"Bearer {login_body['access_token']}"
            }
            profile = client.get("/api/v1/citizens/me", headers=headers)
            identity = client.get("/api/v1/citizens/me/identity", headers=headers)

            assert profile.status_code == 200
            assert profile.json()["email"] == email
            assert identity.status_code == 200
            assert identity.json()["nid_number"] == nid_number

            with Session(engine) as session:
                session_count_before = session.scalar(
                    select(func.count()).select_from(AuthSession)
                )
                citizen_user = session.get(User, user_ids[0])
                assert citizen_user is not None
                citizen_user.is_active = False
                session.commit()
            inactive_login = client.post(
                "/api/v1/auth/citizen/login",
                json={"email": email, "password": "StrongPassword123!"},
            )

            no_profile_user = User(
                email=f"no-profile-{suffix}@example.com",
                password_hash=hash_password("StrongPassword123!"),
                first_name="No",
                last_name="Profile",
            )
            with Session(engine, expire_on_commit=False) as session:
                session.add(no_profile_user)
                session.commit()
            user_ids.append(no_profile_user.id)
            no_profile_login = client.post(
                "/api/v1/auth/citizen/login",
                json={
                    "email": no_profile_user.email,
                    "password": "StrongPassword123!",
                },
            )

            expected_error = {"detail": "Invalid email or password."}
            assert inactive_login.status_code == 401
            assert no_profile_login.status_code == 401
            assert inactive_login.json() == expected_error
            assert no_profile_login.json() == expected_error
            with Session(engine) as session:
                assert session.scalar(
                    select(func.count()).select_from(AuthSession)
                ) == session_count_before
    finally:
        _delete_users(engine, user_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for citizen PostgreSQL coverage",
)
def test_concurrent_one_time_nid_addition_has_exactly_one_winner(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex
    user_id: uuid.UUID | None = None
    barrier = Barrier(2)
    candidate_nids = [f"A{suffix}"[:32], f"B{suffix}"[:32]]

    with Session(engine, expire_on_commit=False) as session:
        registered = CitizenService(session, test_settings).register(
            CitizenRegistrationRequest(
                email=f"phase3-race-{suffix}@example.com",
                password="StrongPassword123!",
                first_name="Concurrent",
                last_name="Citizen",
                date_of_birth=date(1990, 1, 1),
                gender="OTHER",
                nid_number=None,
                birth_certificate_number=_bcn(uuid.uuid4(), "P3-BCN-"),
            )
        )
        user_id = registered.user.id
        retained_bcn = registered.identity.birth_certificate_number

    def add_nid(nid_number: str) -> str:
        assert user_id is not None
        with Session(engine, expire_on_commit=False) as session:
            barrier.wait(timeout=10)
            try:
                CitizenService(session, test_settings).add_national_identifier(
                    user_id,
                    CitizenAddNidRequest(
                        nid_number=nid_number,
                        confirmation="CONFIRM",
                    ),
                )
                return "created"
            except CitizenIdentityUpgradeError:
                return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(add_nid, candidate_nids))

        assert outcomes.count("created") == 1
        assert outcomes.count("conflict") == 1
        with Session(engine) as session:
            identity = session.scalar(
                select(CitizenIdentifier).where(
                    CitizenIdentifier.user_id == user_id
                )
            )
            identifiers = session.scalars(
                select(UserNationalIdentifier).where(
                    UserNationalIdentifier.user_id == user_id
                )
            ).all()
            assert identity is not None
            assert identity.birth_certificate_number == retained_bcn
            assert identity.nid_added_at is not None
            assert len(identifiers) == 1
            assert identifiers[0].nid_number in candidate_nids
            assert identity.national_identifier_id == identifiers[0].id
    finally:
        if user_id is not None:
            _delete_users(engine, [user_id])
        engine.dispose()
