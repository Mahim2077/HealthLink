from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth.models import AuthSession, User
from app.citizens.models import CitizenIdentifier, CitizenProfile, UserNationalIdentifier
from app.core.config import Settings
from app.db.session import create_database_engine, get_db
from app.main import create_app
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


def _professional_payload(
    email: str,
    nid: str,
    bmdc: str,
) -> dict[str, object]:
    return {
        "email": email,
        "password": "StrongPassword123!",
        "first_name": "Live",
        "last_name": "Doctor",
        "nid_number": nid,
        "role_code": "DOCTOR",
        "facility_name": "Live PostgreSQL Hospital",
        "designation": "Consultant",
        "additional_info": "PostgreSQL professional registration coverage.",
        "bmdc_registration_number": bmdc,
    }


def _delete_professional_users(engine, user_ids: list[uuid.UUID]) -> None:
    if not user_ids:
        return
    with engine.begin() as connection:
        profile_ids = select(HealthcareProfessionalProfile.id).where(
            HealthcareProfessionalProfile.user_id.in_(user_ids)
        )
        registration_ids = select(ProfessionalRoleRegistration.id).where(
            ProfessionalRoleRegistration.professional_id.in_(profile_ids)
        )
        connection.execute(
            delete(DoctorRegistrationDetail).where(
                DoctorRegistrationDetail.professional_role_registration_id.in_(
                    registration_ids
                )
            )
        )
        connection.execute(
            delete(ProfessionalRoleRegistration).where(
                ProfessionalRoleRegistration.professional_id.in_(profile_ids)
            )
        )
        connection.execute(
            delete(HealthcareProfessionalProfile).where(
                HealthcareProfessionalProfile.user_id.in_(user_ids)
            )
        )
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
        connection.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))
        connection.execute(delete(User).where(User.id.in_(user_ids)))


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for professional PostgreSQL coverage",
)
def test_postgresql_professional_schema_seed_defaults_and_constraints() -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_ids = [uuid.uuid4(), uuid.uuid4()]
    try:
        with Session(engine, expire_on_commit=False) as session:
            roles = session.scalars(select(ProfessionalRole)).all()
            assert {role.code for role in roles} == {
                "DOCTOR",
                "LAB_TECHNICIAN",
                "NURSE",
                "PHARMACIST",
                "RADIOLOGY_TECHNICIAN",
                "OTHER_HEALTHCARE_PROFESSIONAL",
            }
            doctor_role = next(role for role in roles if role.code == "DOCTOR")
            session.add_all(
                [
                    User(
                        id=user_id,
                        email=f"p4-constraint-{user_id.hex}@example.com",
                        password_hash="constraint-hash",
                        first_name="Constraint",
                        last_name="Professional",
                    )
                    for user_id in user_ids
                ]
            )
            session.commit()
            profile = HealthcareProfessionalProfile(user_id=user_ids[0])
            session.add(profile)
            session.flush()
            registration = ProfessionalRoleRegistration(
                professional_id=profile.id,
                role_id=doctor_role.id,
                facility_name_submitted="Constraint Hospital",
                designation="Doctor",
                additional_info="Constraint coverage",
            )
            session.add(registration)
            session.flush()
            detail = DoctorRegistrationDetail(
                professional_role_registration_id=registration.id,
                bmdc_registration_number=f"BMDC-{user_ids[0].hex}",
            )
            session.add(detail)
            session.commit()
            session.refresh(profile)
            session.refresh(registration)
            session.refresh(detail)
            assert registration.verification_status == "PENDING"
            assert registration.submitted_at.tzinfo is not None
            assert profile.created_at.tzinfo is not None
            assert detail.created_at.tzinfo is not None

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                role = session.scalar(select(ProfessionalRole).where(ProfessionalRole.code == "DOCTOR"))
                profile = session.scalar(
                    select(HealthcareProfessionalProfile).where(
                        HealthcareProfessionalProfile.user_id == user_ids[0]
                    )
                )
                session.add(
                    ProfessionalRoleRegistration(
                        professional_id=profile.id,
                        role_id=role.id,
                        facility_name_submitted="Duplicate",
                        designation="Doctor",
                        verification_status="PENDING",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                role = session.scalar(select(ProfessionalRole).where(ProfessionalRole.code == "NURSE"))
                profile = session.scalar(
                    select(HealthcareProfessionalProfile).where(
                        HealthcareProfessionalProfile.user_id == user_ids[0]
                    )
                )
                session.add(
                    ProfessionalRoleRegistration(
                        professional_id=profile.id,
                        role_id=role.id,
                        facility_name_submitted="Invalid Status",
                        designation="Nurse",
                        verification_status="ACTIVE",
                    )
                )
                session.commit()

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(HealthcareProfessionalProfile(user_id=user_ids[0]))
                session.commit()
    finally:
        _delete_professional_users(engine, user_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for professional PostgreSQL coverage",
)
def test_live_postgresql_registration_and_existing_citizen_onboarding(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex
    user_ids: list[uuid.UUID] = []
    application = create_app(test_settings)

    def postgres_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    application.dependency_overrides[get_db] = postgres_db
    try:
        with TestClient(application) as client:
            doctor = client.post(
                "/api/v1/auth/professional/register",
                json=_professional_payload(
                    f"live-doctor-{suffix}@example.com",
                    f"D{suffix}"[:32],
                    f"BMDC-D-{suffix}",
                ),
            )
            assert doctor.status_code == 201
            assert doctor.json()["verification_status"] == "PENDING"
            user_ids.append(uuid.UUID(doctor.json()["user_id"]))

            citizen = client.post(
                "/api/v1/auth/citizen/register",
                json={
                    "email": f"live-citizen-{suffix}@example.com",
                    "password": "StrongPassword123!",
                    "first_name": "Citizen",
                    "last_name": "Professional",
                    "date_of_birth": "1990-01-01",
                    "gender": "OTHER",
                    "nid_number": f"C{suffix}"[:32],
                },
            )
            assert citizen.status_code == 201
            citizen_id = uuid.UUID(citizen.json()["user_id"])
            user_ids.append(citizen_id)
            login = client.post(
                "/api/v1/auth/citizen/login",
                json={
                    "email": f"live-citizen-{suffix}@example.com",
                    "password": "StrongPassword123!",
                },
            )
            onboard = client.post(
                "/api/v1/professionals/me/onboard",
                headers={"Authorization": f"Bearer {login.json()['access_token']}"},
                json={
                    "role_code": "LAB_TECHNICIAN",
                    "facility_name": "Live Diagnostic Centre",
                    "designation": "Technologist",
                    "additional_info": "Existing citizen onboarding coverage.",
                },
            )
            assert onboard.status_code == 201
            assert uuid.UUID(onboard.json()["user_id"]) == citizen_id
            assert onboard.json()["role_code"] == "LAB_TECHNICIAN"
            assert onboard.json()["verification_status"] == "PENDING"
    finally:
        _delete_professional_users(engine, user_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for professional PostgreSQL coverage",
)
def test_concurrent_duplicate_bmdc_has_one_winner_and_no_orphan_account(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex
    emails = [f"p4-race-a-{suffix}@example.com", f"p4-race-b-{suffix}@example.com"]
    barrier = Barrier(2)
    application = create_app(test_settings)

    def postgres_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    application.dependency_overrides[get_db] = postgres_db

    def register(index: int) -> int:
        with TestClient(application) as client:
            barrier.wait(timeout=10)
            response = client.post(
                "/api/v1/auth/professional/register",
                json=_professional_payload(
                    emails[index],
                    f"{index}{suffix}"[:32],
                    f"SHARED-BMDC-{suffix}",
                ),
            )
            return response.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(register, [0, 1]))
        assert statuses.count(201) == 1
        assert statuses.count(409) == 1
        with Session(engine) as session:
            users = session.scalars(select(User).where(User.email.in_(emails))).all()
            assert len(users) == 1
            assert session.scalar(
                select(DoctorRegistrationDetail).where(
                    DoctorRegistrationDetail.bmdc_registration_number
                    == f"SHARED-BMDC-{suffix}"
                )
            ) is not None
            user_ids = [user.id for user in users]
    finally:
        with Session(engine) as session:
            user_ids = list(session.scalars(select(User.id).where(User.email.in_(emails))))
        _delete_professional_users(engine, user_ids)
        engine.dispose()
