"""PostgreSQL coverage for the doctor discovery endpoints (V6 section 13).

The SQLite suite already covers the service-level flows end-to-end. This
file focuses on what PostgreSQL adds on top:

* FK behaviour (ON DELETE RESTRICT) for ``doctor_practice_schedules`` rows
  pointing at users and facilities.
* CheckConstraint enforcement for invalid weekdays, status, max_patients
  and end-after-start times.
* Live HTTP flow through a TestClient bound to a real PG engine using
  ``HEALTHLINK_TEST_DATABASE_URL``.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, time, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.admins.models import AdminAccount
from app.admins.provisioning import create_trusted_admin
from app.auth.models import AuthSession, User
from app.citizens.models import UserNationalIdentifier
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import create_database_engine, get_db
from app.doctors.models import (
    DoctorPracticeSchedule,
    PracticeScheduleStatus,
    PracticeWeekday,
)
from app.facilities.models import HealthcareFacility
from app.main import create_app
from app.professionals.constants import (
    ProfessionalRoleCode,
    VerificationStatus,
)
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


def _cleanup(
    engine,
    user_ids: list[uuid.UUID],
    facility_ids: list[uuid.UUID],
    schedule_ids: list[uuid.UUID],
) -> None:
    with engine.begin() as connection:
        if schedule_ids:
            connection.execute(
                delete(DoctorPracticeSchedule).where(
                    DoctorPracticeSchedule.id.in_(schedule_ids)
                )
            )
        if user_ids:
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
                delete(UserNationalIdentifier).where(
                    UserNationalIdentifier.user_id.in_(user_ids)
                )
            )
            connection.execute(
                delete(AdminAccount).where(AdminAccount.user_id.in_(user_ids))
            )
            connection.execute(
                delete(AuthSession).where(AuthSession.user_id.in_(user_ids))
            )
            connection.execute(delete(User).where(User.id.in_(user_ids)))
        if facility_ids:
            connection.execute(
                delete(HealthcareFacility).where(
                    HealthcareFacility.id.in_(facility_ids)
                )
            )


def _make_user(
    session: Session,
    *,
    suffix: str,
    first_name: str,
    last_name: str,
) -> User:
    user = User(
        email=f"doc-{suffix}-{first_name.lower()}@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name=first_name,
        last_name=last_name,
    )
    session.add(user)
    session.flush()
    session.add(
        UserNationalIdentifier(
            user_id=user.id,
            nid_number=f"NID-{user.id.hex[:24]}",
        )
    )
    session.flush()
    return user


def _make_facility(
    session: Session,
    *,
    name: str,
    suffix: str,
    is_active: bool = True,
) -> HealthcareFacility:
    facility = HealthcareFacility(
        name=f"{name} {suffix}",
        facility_type="HOSPITAL",
        registration_number=f"REG-{suffix}",
        address="Dhaka",
        phone="+8801700000000",
        email=f"facility-{suffix}@example.com",
        is_active=is_active,
    )
    session.add(facility)
    session.flush()
    return facility


def _make_verified_doctor(
    session: Session,
    *,
    suffix: str,
    user: User,
    facility: HealthcareFacility,
    designation: str = "Consultant",
    bmdc_suffix: str | None = None,
) -> tuple[ProfessionalRoleRegistration, DoctorRegistrationDetail]:
    profile = HealthcareProfessionalProfile(user_id=user.id)
    session.add(profile)
    session.flush()
    role = session.scalar(
        select(ProfessionalRole).where(
            ProfessionalRole.code == ProfessionalRoleCode.DOCTOR.value
        )
    )
    assert role is not None
    registration = ProfessionalRoleRegistration(
        professional_id=profile.id,
        role_id=role.id,
        facility_id=facility.id,
        facility_name_submitted=facility.name,
        designation=designation,
        verification_status=VerificationStatus.VERIFIED.value,
        verified_at=datetime.now(timezone.utc),
    )
    session.add(registration)
    session.flush()
    detail = DoctorRegistrationDetail(
        professional_role_registration_id=registration.id,
        bmdc_registration_number=f"BMDC-{bmdc_suffix or suffix}",
    )
    session.add(detail)
    session.flush()
    return registration, detail


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for doctor search PostgreSQL coverage",
)
def test_postgresql_doctor_search_against_live_pg(
    test_settings: Settings,
) -> None:
    """End-to-end doctor search against a live PG engine using a citizen login."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_ids: list[uuid.UUID] = []
    facility_ids: list[uuid.UUID] = []
    schedule_ids: list[uuid.UUID] = []
    target_user_id: uuid.UUID | None = None
    try:
        suffix = uuid.uuid4().hex[:10]
        with Session(engine, expire_on_commit=False) as session:
            facility_a = _make_facility(
                session, name="PG Clinic", suffix=suffix
            )
            facility_b = _make_facility(
                session, name="Other Chamber", suffix=suffix
            )
            facility_ids.extend([facility_a.id, facility_b.id])

            target = _make_user(
                session,
                suffix=suffix,
                first_name="Tomi",
                last_name="Akiyama",
            )
            user_ids.append(target.id)
            _make_verified_doctor(
                session,
                suffix=suffix,
                user=target,
                facility=facility_a,
                bmdc_suffix=f"{suffix}A",
            )

            other = _make_user(
                session,
                suffix=suffix,
                first_name="Zane",
                last_name="Briggs",
            )
            user_ids.append(other.id)
            _make_verified_doctor(
                session,
                suffix=suffix,
                user=other,
                facility=facility_b,
                designation="Junior",
                bmdc_suffix=f"{suffix}B",
            )

            schedule = DoctorPracticeSchedule(
                doctor_user_id=target.id,
                facility_id=facility_a.id,
                weekday=PracticeWeekday.SUNDAY.value,
                start_time=time(16, 0),
                end_time=time(21, 0),
                max_patients=30,
                status=PracticeScheduleStatus.ACTIVE.value,
            )
            session.add(schedule)
            session.commit()
            schedule_ids.append(schedule.id)
            target_user_id = target.id

        application = create_app(test_settings)

        def override_db() -> Session:
            with Session(engine, expire_on_commit=False) as session:
                yield session

        application.dependency_overrides[get_db] = override_db

        citizen_suffix = uuid.uuid4().hex[:10]
        with TestClient(application) as client:
            register = client.post(
                "/api/v1/auth/citizen/register",
                json={
                    "email": f"citizen-{citizen_suffix}@example.com",
                    "password": "StrongPassword123!",
                    "first_name": "Carla",
                    "last_name": "Citizen",
                    "date_of_birth": "1990-01-01",
                    "gender": "FEMALE",
                    "blood_group": "A+",
                    "address": "Dhaka",
                    "nid_number": f"NID-CIT-{citizen_suffix[:22]}",
                },
            )
            assert register.status_code == 201, register.text
            login = client.post(
                "/api/v1/auth/citizen/login",
                json={
                    "email": f"citizen-{citizen_suffix}@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert login.status_code == 200, login.text
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            by_name = client.get(
                "/api/v1/doctors",
                params={"name": "Akiyama"},
                headers=headers,
            )
            assert by_name.status_code == 200, by_name.text
            last_names = {entry["last_name"] for entry in by_name.json()}
            assert "Akiyama" in last_names
            assert "nid_number" not in by_name.json()[0]
            assert "bmdc_registration_number" not in by_name.json()[0]

            by_facility = client.get(
                "/api/v1/doctors",
                params={"facility_name": "PG Clinic"},
                headers=headers,
            )
            assert by_facility.status_code == 200, by_facility.text
            facility_names = {
                entry["facility_name"] for entry in by_facility.json()
            }
            assert any("PG Clinic" in n for n in facility_names)

            by_weekday = client.get(
                "/api/v1/doctors",
                params={"weekday": "SUNDAY"},
                headers=headers,
            )
            assert by_weekday.status_code == 200, by_weekday.text
            assert any(
                entry["last_name"] == "Akiyama"
                for entry in by_weekday.json()
            )

            profile = client.get(
                f"/api/v1/doctors/{target_user_id}",
                headers=headers,
            )
            assert profile.status_code == 200, profile.text
            body = profile.json()
            assert body["last_name"] == "Akiyama"
            assert body["practice_days"], "schedule should be present"
            assert "nid_number" not in body
            assert "bmdc_number" not in body

            practice_days = client.get(
                f"/api/v1/doctors/{target_user_id}/practice-days",
                headers=headers,
            )
            assert practice_days.status_code == 200, practice_days.text
            assert practice_days.json()[0]["weekday"] == "SUNDAY"
    finally:
        _cleanup(engine, user_ids, facility_ids, schedule_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for doctor schedule PostgreSQL coverage",
)
def test_postgresql_doctor_practice_schedule_check_constraints() -> None:
    """Direct DB writes must hit the check constraints from migration0015.

    Each constraint is exercised in its own ``SAVEPOINT`` via
    ``Session.begin_nested`` so a failed ``IntegrityError`` does not
    invalidate the parent transaction (which would cascade ``user`` /
    ``facility`` deletes). The outer transaction commits once at the end
    so the test can rely on stable foreign keys throughout.
    """
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_ids: list[uuid.UUID] = []
    facility_ids: list[uuid.UUID] = []
    schedule_ids: list[uuid.UUID] = []
    try:
        suffix = uuid.uuid4().hex[:10]
        with Session(engine, expire_on_commit=False) as session:
            with session.begin():
                user = _make_user(
                    session,
                    suffix=suffix,
                    first_name="Const",
                    last_name="User",
                )
                user_ids.append(user.id)
                facility = _make_facility(
                    session, name="Constraint Clinic", suffix=suffix
                )
                facility_ids.append(facility.id)

                # max_patients >= 1 is enforced.
                with pytest.raises(IntegrityError):
                    with session.begin_nested():
                        bad = DoctorPracticeSchedule(
                            doctor_user_id=user.id,
                            facility_id=facility.id,
                            weekday=PracticeWeekday.MONDAY.value,
                            start_time=time(10, 0),
                            end_time=time(12, 0),
                            max_patients=0,
                            status=PracticeScheduleStatus.ACTIVE.value,
                        )
                        session.add(bad)
                        session.flush()

                # end_time > start_time is enforced.
                with pytest.raises(IntegrityError):
                    with session.begin_nested():
                        bad = DoctorPracticeSchedule(
                            doctor_user_id=user.id,
                            facility_id=facility.id,
                            weekday=PracticeWeekday.MONDAY.value,
                            start_time=time(10, 0),
                            end_time=time(10, 0),
                            max_patients=10,
                            status=PracticeScheduleStatus.ACTIVE.value,
                        )
                        session.add(bad)
                        session.flush()

                # weekday enum is enforced.
                with pytest.raises(IntegrityError):
                    with session.begin_nested():
                        bad = DoctorPracticeSchedule(
                            doctor_user_id=user.id,
                            facility_id=facility.id,
                            weekday="FUNDAY",
                            start_time=time(10, 0),
                            end_time=time(12, 0),
                            max_patients=10,
                            status=PracticeScheduleStatus.ACTIVE.value,
                        )
                        session.add(bad)
                        session.flush()

                # Valid row persists cleanly.
                ok = DoctorPracticeSchedule(
                    doctor_user_id=user.id,
                    facility_id=facility.id,
                    weekday=PracticeWeekday.TUESDAY.value,
                    start_time=time(16, 0),
                    end_time=time(21, 0),
                    max_patients=20,
                    status=PracticeScheduleStatus.ACTIVE.value,
                )
                session.add(ok)
                session.flush()
                schedule_ids.append(ok.id)

                # status enum is enforced.
                with pytest.raises(IntegrityError):
                    with session.begin_nested():
                        bad = DoctorPracticeSchedule(
                            doctor_user_id=user.id,
                            facility_id=facility.id,
                            weekday=PracticeWeekday.WEDNESDAY.value,
                            start_time=time(9, 0),
                            end_time=time(11, 0),
                            max_patients=10,
                            status="EXPIRED",
                        )
                        session.add(bad)
                        session.flush()
    finally:
        _cleanup(engine, user_ids, facility_ids, schedule_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for doctor schedule PostgreSQL coverage",
)
def test_postgresql_doctor_practice_schedule_fk_restrict() -> None:
    """Deleting a doctor or facility must RESTRICT when schedules reference them."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_ids: list[uuid.UUID] = []
    facility_ids: list[uuid.UUID] = []
    schedule_ids: list[uuid.UUID] = []
    try:
        suffix = uuid.uuid4().hex[:10]
        with Session(engine, expire_on_commit=False) as session:
            user = _make_user(
                session,
                suffix=suffix,
                first_name="FK",
                last_name="Subject",
            )
            user_ids.append(user.id)
            facility = _make_facility(session, name="FK Clinic", suffix=suffix)
            facility_ids.append(facility.id)
            schedule = DoctorPracticeSchedule(
                doctor_user_id=user.id,
                facility_id=facility.id,
                weekday=PracticeWeekday.THURSDAY.value,
                start_time=time(10, 0),
                end_time=time(13, 0),
                max_patients=12,
                status=PracticeScheduleStatus.ACTIVE.value,
            )
            session.add(schedule)
            session.flush()
            schedule_ids.append(schedule.id)
            session.commit()

            # Tempt the cascade: deleting the user must fail.
            with pytest.raises(IntegrityError):
                session.delete(user)
                session.flush()
            session.rollback()

            # Same for the facility: deleting it must fail while referenced.
            with pytest.raises(IntegrityError):
                session.delete(facility)
                session.flush()
            session.rollback()
    finally:
        _cleanup(engine, user_ids, facility_ids, schedule_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for doctor schedule PostgreSQL coverage",
)
def test_postgresql_admin_can_also_list_practice_schedule(
    test_settings: Settings,
) -> None:
    """Admins must be able to drive the citizen search via the live engine."""
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_ids: list[uuid.UUID] = []
    facility_ids: list[uuid.UUID] = []
    schedule_ids: list[uuid.UUID] = []
    try:
        suffix = uuid.uuid4().hex[:10]
        with Session(engine, expire_on_commit=False) as session:
            admin = create_trusted_admin(
                session,
                email=f"admin-{suffix}@example.com",
                password="StrongAdminPassword123!",
                first_name="Admin",
                last_name="User",
                is_super_admin=False,
            )
            user_ids.append(admin.user.id)

            facility = _make_facility(
                session, name="Admin Discovery Clinic", suffix=suffix
            )
            facility_ids.append(facility.id)
            doctor_user = _make_user(
                session,
                suffix=suffix,
                first_name="Admin",
                last_name="Searchable",
            )
            user_ids.append(doctor_user.id)
            _make_verified_doctor(
                session,
                suffix=suffix,
                user=doctor_user,
                facility=facility,
                bmdc_suffix=f"{suffix}A",
            )
            schedule = DoctorPracticeSchedule(
                doctor_user_id=doctor_user.id,
                facility_id=facility.id,
                weekday=PracticeWeekday.MONDAY.value,
                start_time=time(15, 0),
                end_time=time(19, 0),
                max_patients=20,
                status=PracticeScheduleStatus.ACTIVE.value,
            )
            session.add(schedule)
            session.flush()
            schedule_ids.append(schedule.id)
            session.commit()

        application = create_app(test_settings)

        def override_db() -> Session:
            with Session(engine, expire_on_commit=False) as session:
                yield session

        application.dependency_overrides[get_db] = override_db

        with TestClient(application) as client:
            login = client.post(
                "/api/v1/auth/admin/login",
                json={
                    "email": f"admin-{suffix}@example.com",
                    "password": "StrongAdminPassword123!",
                },
            )
            assert login.status_code == 200, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            response = client.get(
                "/api/v1/doctors",
                params={"facility_name": "Admin Discovery"},
                headers=headers,
            )
            assert response.status_code == 200, response.text
            payload = response.json()
            assert len(payload) == 1
            assert payload[0]["last_name"] == "Searchable"
    finally:
        _cleanup(engine, user_ids, facility_ids, schedule_ids)
        engine.dispose()