from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timezone
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    AppointmentStatus,
    DoctorPracticeSession,
)
from app.auth.models import AuthSession, User
from app.citizens.models import (
    CitizenIdentifier,
    CitizenProfile,
    UserNationalIdentifier,
)
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_database_engine, get_db
from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
from app.facilities.models import HealthcareFacility
from app.main import create_app
from app.professionals.constants import (
    ProfessionalRoleCode,
    VerificationStatus,
)
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")
CITIZEN_PASSWORD = "StrongPassword123!"


def _nid_value(value: uuid.UUID) -> str:
    return f"NID-{value.hex}"[:32]


def _register_citizen_via_service(
    db: Session, *, email: str
) -> uuid.UUID:
    from app.auth.services.password import hash_password as _hash

    from app.citizens.schemas import CitizenRegistrationRequest
    from app.citizens.service import CitizenService

    settings = Settings(
        _env_file=None,
        app_name="HealthLink Test",
        app_env="test",
        debug=False,
        database_url=POSTGRES_TEST_DATABASE_URL,
        frontend_url="http://localhost:3000",
        jwt_secret_key="test-secret-key-with-at-least-thirty-two-characters",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    password_hash = _hash(CITIZEN_PASSWORD)
    user = User(
        email=email,
        password_hash=password_hash,
        first_name="PG",
        last_name="Citizen",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    request = CitizenRegistrationRequest(
        email=email,
        password=CITIZEN_PASSWORD,
        first_name="PG",
        last_name="Citizen",
        date_of_birth=date(1990, 1, 1),
        gender="FEMALE",
        blood_group="A+",
        address="Dhaka",
        nid_number=_nid_value(user.id),
        birth_certificate_number=None,
    )
    CitizenService(db, settings).register(request)
    db.commit()
    return user.id


def _create_login_citizen(
    client: TestClient, *, email: str
) -> tuple[uuid.UUID, str]:
    """Register a citizen through the public route and return (user_id, token)."""
    unique = uuid.uuid4().hex
    response = client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": email,
            "password": CITIZEN_PASSWORD,
            "first_name": "PG",
            "last_name": "Citizen",
            "date_of_birth": "1990-01-01",
            "gender": "FEMALE",
            "blood_group": "A+",
            "address": "Dhaka",
            "nid_number": _nid_value(uuid.UUID(unique)),
        },
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["user_id"]
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": email, "password": CITIZEN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return uuid.UUID(user_id), login.json()["access_token"]


def _make_doctor(
    db: Session, *, facility_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(
        email=f"doctor-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="pg-doctor-hash",
        first_name="PG",
        last_name="Doctor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = HealthcareProfessionalProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    role = db.scalar(
        select(ProfessionalRole).where(
            ProfessionalRole.code == ProfessionalRoleCode.DOCTOR.value
        )
    )
    assert role is not None

    registration = ProfessionalRoleRegistration(
        professional_id=profile.id,
        role_id=role.id,
        facility_id=facility_id,
        facility_name_submitted="PG Booking Facility",
        designation="Consultant",
        verification_status=VerificationStatus.VERIFIED.value,
        verified_at=datetime.now(timezone.utc),
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return user.id, registration.id


def _seed_facility_and_schedule(
    engine, *, max_patients: int = 10
) -> tuple[uuid.UUID, uuid.UUID]:
    facility_id = uuid.uuid4()
    doctor_user_id = uuid.uuid4()
    registration_id = uuid.uuid4()
    schedule_id = uuid.uuid4()

    with engine.begin() as connection:
        connection.execute(
            HealthcareFacility.__table__.insert().values(
                id=facility_id,
                name="PG Booking Facility",
                facility_type="HOSPITAL",
                registration_number=f"REG-{uuid.uuid4().hex[:8]}",
                address="Dhaka",
                phone="+8801700000000",
                email="pg-facility@example.com",
                is_active=True,
            )
        )
        # Seed the doctor user + profile + role + registration rows.
        connection.execute(
            User.__table__.insert().values(
                id=doctor_user_id,
                email=f"pg-doctor-{doctor_user_id.hex[:8]}@example.com",
                password_hash="pg-doctor-hash",
                first_name="PG",
                last_name="Doctor",
            )
        )
        profile_id = uuid.uuid4()
        connection.execute(
            HealthcareProfessionalProfile.__table__.insert().values(
                id=profile_id,
                user_id=doctor_user_id,
            )
        )
        connection.execute(
            ProfessionalRoleRegistration.__table__.insert().values(
                id=registration_id,
                professional_id=profile_id,
                role_id=select(ProfessionalRole.id).where(
                    ProfessionalRole.code == ProfessionalRoleCode.DOCTOR.value
                ).scalar_subquery(),
                facility_id=facility_id,
                facility_name_submitted="PG Booking Facility",
                designation="Consultant",
                verification_status=VerificationStatus.VERIFIED.value,
                verified_at=datetime.now(timezone.utc),
            )
        )
        connection.execute(
            DoctorPracticeSchedule.__table__.insert().values(
                id=schedule_id,
                doctor_user_id=doctor_user_id,
                facility_id=facility_id,
                weekday="MONDAY",
                start_time=time(9, 0),
                end_time=time(17, 0),
                max_patients=max_patients,
                status=PracticeScheduleStatus.ACTIVE.value,
            )
        )
    return doctor_user_id, facility_id


def _cleanup(
    engine,
    *,
    user_ids: list[uuid.UUID],
    facility_ids: list[uuid.UUID] | None = None,
) -> None:
    """Drop every row this test created, in dependency order.

    The booking tests create rows across many tables and rely on FK
    ``ondelete="RESTRICT"`` enforcement, so the cleanup must delete
    dependents before the rows they point at.
    """

    facility_ids = facility_ids or []
    with engine.begin() as connection:
        # 1. Drop queue rows that depend on practice sessions / appointments.
        if facility_ids:
            practice_session_ids = select(DoctorPracticeSession.id).where(
                DoctorPracticeSession.facility_id.in_(facility_ids)
            )
            appointment_ids = select(Appointment.id).where(
                Appointment.facility_id.in_(facility_ids)
            )
            connection.execute(
                delete(AppointmentQueueEntry).where(
                    AppointmentQueueEntry.practice_session_id.in_(
                        practice_session_ids.scalar_subquery()
                    )
                )
            )
            connection.execute(
                delete(AppointmentQueueEntry).where(
                    AppointmentQueueEntry.appointment_id.in_(
                        appointment_ids.scalar_subquery()
                    )
                )
            )
            connection.execute(
                delete(DoctorPracticeSession).where(
                    DoctorPracticeSession.facility_id.in_(facility_ids)
                )
            )
            connection.execute(
                delete(Appointment).where(
                    Appointment.facility_id.in_(facility_ids)
                )
            )

        # 2. Drop dependents that point at the seeded users.
        if user_ids:
            citizen_profile_ids = select(CitizenProfile.id).where(
                CitizenProfile.user_id.in_(user_ids)
            )
            connection.execute(
                delete(Appointment).where(
                    Appointment.citizen_id.in_(
                        citizen_profile_ids.scalar_subquery()
                    )
                )
            )
            connection.execute(
                delete(AuthSession).where(AuthSession.user_id.in_(user_ids))
            )
            connection.execute(
                delete(CitizenIdentifier).where(
                    CitizenIdentifier.user_id.in_(user_ids)
                )
            )
            connection.execute(
                delete(CitizenProfile).where(
                    CitizenProfile.user_id.in_(user_ids)
                )
            )
            connection.execute(
                delete(UserNationalIdentifier).where(
                    UserNationalIdentifier.user_id.in_(user_ids)
                )
            )
            # Doctor-side profile / registration rows reference these users.
            profile_ids = select(HealthcareProfessionalProfile.id).where(
                HealthcareProfessionalProfile.user_id.in_(user_ids)
            )
            connection.execute(
                delete(ProfessionalRoleRegistration).where(
                    ProfessionalRoleRegistration.professional_id.in_(
                        profile_ids.scalar_subquery()
                    )
                )
            )
            connection.execute(
                delete(HealthcareProfessionalProfile).where(
                    HealthcareProfessionalProfile.user_id.in_(user_ids)
                )
            )
            connection.execute(
                delete(User).where(User.id.in_(user_ids))
            )

        # 3. Finally drop the facility-scoped infrastructure.
        if facility_ids:
            connection.execute(
                delete(ProfessionalRoleRegistration).where(
                    ProfessionalRoleRegistration.facility_id.in_(facility_ids)
                )
            )
            connection.execute(
                delete(DoctorPracticeSchedule).where(
                    DoctorPracticeSchedule.facility_id.in_(facility_ids)
                )
            )
            connection.execute(
                delete(HealthcareFacility).where(
                    HealthcareFacility.id.in_(facility_ids)
                )
            )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for appointment PostgreSQL coverage",
)
def test_postgresql_concurrent_booking_assigns_unique_serials() -> None:
    """Two threads booking the same doctor/date must never share a serial.

    Even with the unique constraint providing the safety net, advisory locks
    must serialize the bookings so each thread observes the prior MAX(serial)
    before computing its next slot.
    """
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    settings = Settings(
        _env_file=None,
        app_name="HealthLink Test",
        app_env="test",
        debug=False,
        database_url=POSTGRES_TEST_DATABASE_URL,
        frontend_url="http://localhost:3000",
        jwt_secret_key="test-secret-key-with-at-least-thirty-two-characters",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )

    doctor_user_id, facility_id = _seed_facility_and_schedule(engine)

    application = create_app(settings)

    user_ids: list[uuid.UUID] = []
    tokens: list[tuple[uuid.UUID, str]] = []
    try:
        with TestClient(application) as client:
            for index in range(2):
                email = f"pg-booking-{index}-{uuid.uuid4().hex[:8]}@example.com"
                user_id, token = _create_login_citizen(
                    client, email=email
                )
                user_ids.append(user_id)
                tokens.append((user_id, token))

        # Fire both booking requests on independent Sessions backed by the
        # same database to exercise the advisory lock and the unique
        # constraint under contention. We call the AppointmentService
        # directly per-thread (each thread owns its own session); routing
        # through TestClient would require sharing application.dependency
        # _overrides across threads which is racy with FastAPI's ASGI
        # bridge.
        barrier = Barrier(len(tokens))

        def book(
            entry: tuple[uuid.UUID, str]
        ) -> int:
            from app.appointments.schemas import AppointmentBookingRequest
            from app.appointments.service import AppointmentService

            user_id, _token = entry
            session = Session(engine, expire_on_commit=False)
            try:
                service = AppointmentService(session, settings)
                booking_request = AppointmentBookingRequest(
                    doctor_user_id=doctor_user_id,
                    facility_id=facility_id,
                    appointment_date=date(2099, 1, 5),
                )
                barrier.wait()
                try:
                    response = service.book_appointment(
                        citizen_user_id=user_id,
                        request=booking_request,
                    )
                except Exception:
                    session.rollback()
                    raise
                session.commit()
                return response.serial_number
            finally:
                session.close()

        with ThreadPoolExecutor(max_workers=len(tokens)) as executor:
            results = list(executor.map(book, tokens))

        # Both bookings succeeded and assigned different serials.
        assert sorted(results) == [1, 2]

        # Confirm the rows landed in the database with the expected serials.
        with Session(engine, expire_on_commit=False) as session:
            rows = session.execute(
                select(Appointment.serial_number).where(
                    Appointment.facility_id == facility_id,
                    Appointment.appointment_date == date(2099, 1, 5),
                ).order_by(Appointment.serial_number)
            ).all()
            serials = [row[0] for row in rows]
            assert serials == [1, 2]
            for row in session.execute(
                select(Appointment).where(
                    Appointment.facility_id == facility_id,
                    Appointment.appointment_date == date(2099, 1, 5),
                )
            ).scalars():
                assert row.status == AppointmentStatus.BOOKED.value
    finally:
        _cleanup(
            engine, user_ids=user_ids, facility_ids=[facility_id]
        )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for appointment PostgreSQL coverage",
)
def test_postgresql_partial_unique_index_blocks_second_current_queue_entry() -> None:
    """Two CURRENT rows for the same session must fail the partial unique index.

    This is the database-level enforcement that backs the queue invariant
    described in V6 section 19.
    """
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    from app.appointments.models import (
        AppointmentQueueEntry,
        DoctorPracticeSession,
        QueueStatus,
        SessionStatus,
    )

    facility_id = uuid.uuid4()
    doctor_user_id = uuid.uuid4()
    registration_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    session_id = uuid.uuid4()
    first_appointment_id = uuid.uuid4()
    second_appointment_id = uuid.uuid4()
    citizen_profile_id = uuid.uuid4()
    citizen_user_id = uuid.uuid4()
    first_queue_entry_id = uuid.uuid4()
    second_queue_entry_id = uuid.uuid4()

    try:
        with engine.begin() as connection:
            connection.execute(
                HealthcareFacility.__table__.insert().values(
                    id=facility_id,
                    name="PG Queue Facility",
                    facility_type="HOSPITAL",
                    registration_number=f"REG-{uuid.uuid4().hex[:8]}",
                    address="Dhaka",
                    phone="+8801700000000",
                    email="pg-queue@example.com",
                    is_active=True,
                )
            )
            connection.execute(
                User.__table__.insert().values(
                    id=doctor_user_id,
                    email=f"pg-queue-doctor-{doctor_user_id.hex[:8]}@example.com",
                    password_hash="pg-queue-hash",
                    first_name="PG",
                    last_name="QueueDoctor",
                )
            )
            connection.execute(
                User.__table__.insert().values(
                    id=citizen_user_id,
                    email=f"pg-queue-citizen-{citizen_user_id.hex[:8]}@example.com",
                    password_hash="pg-queue-hash",
                    first_name="PG",
                    last_name="QueueCitizen",
                )
            )
            connection.execute(
                HealthcareProfessionalProfile.__table__.insert().values(
                    id=profile_id,
                    user_id=doctor_user_id,
                )
            )
            connection.execute(
                ProfessionalRoleRegistration.__table__.insert().values(
                    id=registration_id,
                    professional_id=profile_id,
                    role_id=select(ProfessionalRole.id).where(
                        ProfessionalRole.code == ProfessionalRoleCode.DOCTOR.value
                    ).scalar_subquery(),
                    facility_id=facility_id,
                    facility_name_submitted="PG Queue Facility",
                    designation="Consultant",
                    verification_status=VerificationStatus.VERIFIED.value,
                    verified_at=datetime.now(timezone.utc),
                )
            )
            # citizen_profile row is required by the appointments FK
            connection.execute(
                CitizenProfile.__table__.insert().values(
                    id=citizen_profile_id,
                    user_id=citizen_user_id,
                    date_of_birth=date(1990, 1, 1),
                    gender="FEMALE",
                )
            )
            connection.execute(
                Appointment.__table__.insert().values(
                    id=first_appointment_id,
                    citizen_id=citizen_profile_id,
                    doctor_role_registration_id=registration_id,
                    facility_id=facility_id,
                    appointment_date=date(2099, 1, 5),
                    serial_number=1,
                    status=AppointmentStatus.BOOKED.value,
                    booked_at=datetime.now(timezone.utc),
                )
            )
            connection.execute(
                Appointment.__table__.insert().values(
                    id=second_appointment_id,
                    citizen_id=citizen_profile_id,
                    doctor_role_registration_id=registration_id,
                    facility_id=facility_id,
                    appointment_date=date(2099, 1, 5),
                    serial_number=2,
                    status=AppointmentStatus.BOOKED.value,
                    booked_at=datetime.now(timezone.utc),
                )
            )
            connection.execute(
                DoctorPracticeSession.__table__.insert().values(
                    id=session_id,
                    doctor_role_registration_id=registration_id,
                    facility_id=facility_id,
                    session_date=date(2099, 1, 5),
                    status=SessionStatus.NOT_STARTED.value,
                )
            )
            # First CURRENT row is permitted.
            connection.execute(
                AppointmentQueueEntry.__table__.insert().values(
                    id=first_queue_entry_id,
                    appointment_id=first_appointment_id,
                    practice_session_id=session_id,
                    queue_status=QueueStatus.CURRENT.value,
                )
            )

        # A second CURRENT row in the same session must be rejected by the
        # partial unique index added in migration 0018.
        from sqlalchemy.exc import IntegrityError as _IntegrityError

        with pytest.raises(_IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    AppointmentQueueEntry.__table__.insert().values(
                        id=second_queue_entry_id,
                        appointment_id=second_appointment_id,
                        practice_session_id=session_id,
                        queue_status=QueueStatus.CURRENT.value,
                    )
                )
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id, citizen_user_id],
            facility_ids=[facility_id],
        )