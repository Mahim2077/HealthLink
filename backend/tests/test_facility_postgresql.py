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

from app.admins.models import AdminAccount, AdminActionLog
from app.admins.provisioning import create_trusted_admin
from app.auth.models import AuthSession, User
from app.citizens.models import UserNationalIdentifier
from app.core.config import Settings
from app.db.session import create_database_engine, get_db
from app.facilities.models import HealthcareFacility
from app.main import create_app
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


def _cleanup(engine, user_ids: list[uuid.UUID], facility_ids: list[uuid.UUID]) -> None:
    with engine.begin() as connection:
        if user_ids:
            profile_ids = select(HealthcareProfessionalProfile.id).where(
                HealthcareProfessionalProfile.user_id.in_(user_ids)
            )
            registration_ids = select(ProfessionalRoleRegistration.id).where(
                ProfessionalRoleRegistration.professional_id.in_(profile_ids)
            )
            connection.execute(
                delete(AdminActionLog).where(
                    (AdminActionLog.admin_user_id.in_(user_ids))
                    | (AdminActionLog.target_user_id.in_(user_ids))
                    | (AdminActionLog.target_resource_id.in_(facility_ids))
                )
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
                delete(UserNationalIdentifier).where(
                    UserNationalIdentifier.user_id.in_(user_ids)
                )
            )
            connection.execute(delete(AdminAccount).where(AdminAccount.user_id.in_(user_ids)))
            connection.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))
            connection.execute(delete(User).where(User.id.in_(user_ids)))
        if facility_ids:
            connection.execute(
                delete(HealthcareFacility).where(HealthcareFacility.id.in_(facility_ids))
            )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for facility PostgreSQL coverage",
)
def test_postgresql_facility_constraints_defaults_fk_and_timezones() -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    facility_ids: list[uuid.UUID] = []
    user_ids: list[uuid.UUID] = []
    try:
        with Session(engine, expire_on_commit=False) as session:
            facility = HealthcareFacility(
                name="PostgreSQL Hospital",
                facility_type="HOSPITAL",
                address="Dhaka",
            )
            session.add(facility)
            session.commit()
            session.refresh(facility)
            facility_ids.append(facility.id)
            assert facility.is_active is True
            assert facility.created_at.tzinfo is not None
            assert facility.updated_at.tzinfo is not None
            user = User(
                email=f"phase6-fk-{uuid.uuid4().hex}@example.com",
                password_hash="constraint-hash",
                first_name="Facility",
                last_name="Constraint",
            )
            session.add(user)
            session.flush()
            profile = HealthcareProfessionalProfile(user_id=user.id)
            session.add(profile)
            session.commit()
            user_ids.append(user.id)
            profile_id = profile.id
        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    HealthcareFacility(
                        name="Invalid Type",
                        facility_type="LAB",
                        address="Dhaka",
                    )
                )
                session.commit()
        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                role = session.scalar(
                    select(ProfessionalRole).where(ProfessionalRole.code == "DOCTOR")
                )
                assert role is not None
                session.add(
                    ProfessionalRoleRegistration(
                        professional_id=profile_id,
                        role_id=role.id,
                        facility_id=uuid.uuid4(),
                        facility_name_submitted="Invalid link",
                        designation="Doctor",
                        additional_info="Constraint coverage",
                    )
                )
                session.commit()
    finally:
        _cleanup(engine, user_ids, facility_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for facility PostgreSQL coverage",
)
def test_postgresql_concurrent_verify_reject_has_one_audited_winner(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    application = create_app(test_settings)
    suffix = uuid.uuid4().hex[:18]
    user_ids: list[uuid.UUID] = []
    facility_ids: list[uuid.UUID] = []

    def postgres_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    application.dependency_overrides[get_db] = postgres_db
    try:
        with Session(engine, expire_on_commit=False) as session:
            admin = create_trusted_admin(
                session,
                email=f"phase6-admin-{suffix}@example.com",
                password="PhaseSixAdminPassword123!",
                first_name="Concurrent",
                last_name="Reviewer",
                is_super_admin=False,
            )
            user_ids.append(admin.user.id)

        with TestClient(application) as client:
            login = client.post(
                "/api/v1/auth/admin/login",
                json={
                    "email": f"phase6-admin-{suffix}@example.com",
                    "password": "PhaseSixAdminPassword123!",
                },
            )
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            registration = client.post(
                "/api/v1/auth/professional/register",
                json={
                    "email": f"phase6-doctor-{suffix}@example.com",
                    "password": "StrongPassword123!",
                    "first_name": "Concurrent",
                    "last_name": "Doctor",
                    "nid_number": f"P6-NID-{suffix}",
                    "role_code": "DOCTOR",
                    "facility_name": "Submitted Hospital",
                    "designation": "Consultant",
                    "additional_info": "Concurrent review coverage.",
                    "bmdc_registration_number": f"P6-BMDC-{suffix}",
                },
            )
            assert registration.status_code == 201
            user_ids.append(uuid.UUID(registration.json()["user_id"]))
            facility = client.post(
                "/api/v1/admin/facilities",
                headers=headers,
                json={
                    "name": f"Concurrent Hospital {suffix}",
                    "facility_type": "HOSPITAL",
                    "registration_number": None,
                    "address": "Dhaka",
                    "phone": None,
                    "email": None,
                    "is_active": True,
                },
            )
            assert facility.status_code == 201
            facility_ids.append(uuid.UUID(facility.json()["id"]))

        registration_id = registration.json()["role_registration_id"]
        barrier = Barrier(2)

        def decide(kind: str) -> int:
            barrier.wait(timeout=10)
            with TestClient(application) as concurrent_client:
                if kind == "verify":
                    response = concurrent_client.post(
                        f"/api/v1/admin/professional-registrations/{registration_id}/verify",
                        headers=headers,
                        json={"facility_id": str(facility_ids[0])},
                    )
                else:
                    response = concurrent_client.post(
                        f"/api/v1/admin/professional-registrations/{registration_id}/reject",
                        headers=headers,
                        json={"reason": "Concurrent rejection evidence."},
                    )
                return response.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(decide, ["verify", "reject"]))
        assert sorted(statuses) == [200, 409]

        with Session(engine) as session:
            stored = session.get(
                ProfessionalRoleRegistration, uuid.UUID(registration_id)
            )
            assert stored is not None
            assert stored.verification_status in {"VERIFIED", "REJECTED"}
            reviews = list(
                session.scalars(
                    select(AdminActionLog).where(
                        AdminActionLog.target_resource_id == uuid.UUID(registration_id),
                        AdminActionLog.action_type.in_(
                            ["PROFESSIONAL_VERIFY", "PROFESSIONAL_REJECT"]
                        ),
                    )
                )
            )
            assert len(reviews) == 1
    finally:
        _cleanup(engine, user_ids, facility_ids)
        engine.dispose()
