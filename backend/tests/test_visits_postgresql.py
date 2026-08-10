"""PostgreSQL coverage for Phase 12 visits & prescriptions.

These tests require ``HEALTHLINK_TEST_DATABASE_URL`` (the Supabase
pooler). They directly exercise the unique-by-appointment constraint
on ``medical_visits`` plus the partial index on draft visits so that
regressions in migration ``0020`` are caught at the database layer.
"""
from __future__ import annotations

import os
import uuid
from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    AppointmentStatus,
    DoctorPracticeSession,
    QueueStatus,
    SessionStatus,
)
from app.auth.models import AuthSession, User
from app.citizens.models import CitizenProfile, UserNationalIdentifier
from app.db.base import Base
from app.db.session import create_database_engine
from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
from app.facilities.models import HealthcareFacility
from app.professionals.constants import (
    ProfessionalRoleCode,
    VerificationStatus,
)
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)
from app.visits.models import MedicalVisit, VisitStatus


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


def _seed_visits_fixture(
    engine,
    *,
    max_patients: int = 4,
) -> tuple[
    uuid.UUID,
    uuid.UUID,
    uuid.UUID,
    uuid.UUID,
    uuid.UUID,
    uuid.UUID,
    uuid.UUID,
]:
    """Seed one doctor + facility + session + appointment + queue entry.

    Returns ``(doctor_user_id, registration_id, facility_id, session_id,
    appointment_id, queue_entry_id, citizen_profile_id)``.
    """

    facility_id = uuid.uuid4()
    doctor_user_id = uuid.uuid4()
    citizen_user_id = uuid.uuid4()
    registration_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    schedule_id = uuid.uuid4()
    session_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    queue_entry_id = uuid.uuid4()
    citizen_profile_id = uuid.uuid4()

    today = date.today()
    while today.strftime("%A").upper() != "MONDAY":
        today = date.fromordinal(today.toordinal() + 1)

    with engine.begin() as connection:
        connection.execute(
            HealthcareFacility.__table__.insert().values(
                id=facility_id,
                name="PG Visits Facility",
                facility_type="HOSPITAL",
                registration_number=f"REG-{uuid.uuid4().hex[:8]}",
                address="Dhaka",
                phone="+8801700000000",
                email="pg-visits@example.com",
                is_active=True,
            )
        )
        connection.execute(
            User.__table__.insert().values(
                id=doctor_user_id,
                email=f"pg-visits-doctor-{doctor_user_id.hex[:8]}@example.com",
                password_hash="pg-visits-hash",
                first_name="PG",
                last_name="VisitsDoctor",
            )
        )
        connection.execute(
            User.__table__.insert().values(
                id=citizen_user_id,
                email=f"pg-visits-citizen-{citizen_user_id.hex[:8]}@example.com",
                password_hash="pg-visits-hash",
                first_name="PG",
                last_name="VisitsCitizen",
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
                facility_name_submitted="PG Visits Facility",
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
                end_time=time(13, 0),
                max_patients=max_patients,
                status=PracticeScheduleStatus.ACTIVE.value,
            )
        )
        connection.execute(
            CitizenProfile.__table__.insert().values(
                id=citizen_profile_id,
                user_id=citizen_user_id,
                date_of_birth=date(1990, 1, 1),
                gender="FEMALE",
            )
        )
        connection.execute(
            DoctorPracticeSession.__table__.insert().values(
                id=session_id,
                doctor_role_registration_id=registration_id,
                facility_id=facility_id,
                session_date=today,
                status=SessionStatus.ACTIVE.value,
                started_at=datetime.now(timezone.utc),
            )
        )
        connection.execute(
            Appointment.__table__.insert().values(
                id=appointment_id,
                citizen_id=citizen_profile_id,
                doctor_role_registration_id=registration_id,
                facility_id=facility_id,
                appointment_date=today,
                serial_number=1,
                status=AppointmentStatus.BOOKED.value,
                booked_at=datetime.now(timezone.utc),
            )
        )
        connection.execute(
            AppointmentQueueEntry.__table__.insert().values(
                id=queue_entry_id,
                appointment_id=appointment_id,
                practice_session_id=session_id,
                queue_status=QueueStatus.CURRENT.value,
                became_current_at=datetime.now(timezone.utc),
            )
        )

    return (
        doctor_user_id,
        registration_id,
        facility_id,
        session_id,
        appointment_id,
        queue_entry_id,
        citizen_profile_id,
    )


def _cleanup(engine, *, user_ids: list[uuid.UUID], facility_ids: list[uuid.UUID]) -> None:
    with engine.begin() as connection:
        # Delete leaf rows first so we never trip a foreign key on the
        # user / facility rows. Visits are FK'd by facility, so they go
        # before appointments; appointments are FK'd by queue entries;
        # sessions reference the facility; schedules reference users.
        if facility_ids:
            connection.execute(
                delete(MedicalVisit).where(
                    MedicalVisit.facility_id.in_(facility_ids)
                )
            )
            appointment_ids = select(Appointment.id).where(
                Appointment.facility_id.in_(facility_ids)
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
            connection.execute(
                delete(DoctorPracticeSchedule).where(
                    DoctorPracticeSchedule.facility_id.in_(facility_ids)
                )
            )
        if user_ids:
            citizen_profile_ids = select(CitizenProfile.id).where(
                CitizenProfile.user_id.in_(user_ids)
            )
            connection.execute(
                delete(MedicalVisit).where(
                    MedicalVisit.citizen_id.in_(citizen_profile_ids.scalar_subquery())
                )
            )
            connection.execute(
                delete(AuthSession).where(AuthSession.user_id.in_(user_ids))
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
        if facility_ids:
            connection.execute(
                delete(HealthcareFacility).where(
                    HealthcareFacility.id.in_(facility_ids)
                )
            )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for visits PostgreSQL coverage",
)
def test_postgresql_unique_constraint_blocks_second_visit_per_appointment() -> None:
    """The UNIQUE(appointment_id) on medical_visits is the safety net
    against duplicate visits. Even outside the application layer a
    second visit row for the same appointment must be rejected.
    """

    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    (
        doctor_user_id,
        registration_id,
        facility_id,
        _session_id,
        appointment_id,
        _queue_entry_id,
        citizen_profile_id,
    ) = _seed_visits_fixture(engine)

    try:
        first_visit_id = uuid.uuid4()
        with engine.begin() as connection:
            connection.execute(
                MedicalVisit.__table__.insert().values(
                    id=first_visit_id,
                    citizen_id=citizen_profile_id,
                    doctor_role_registration_id=registration_id,
                    facility_id=facility_id,
                    appointment_id=appointment_id,
                    visit_date=datetime.now(timezone.utc),
                    status=VisitStatus.DRAFT.value,
                )
            )

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    MedicalVisit.__table__.insert().values(
                        id=uuid.uuid4(),
                        citizen_id=citizen_profile_id,
                        doctor_role_registration_id=registration_id,
                        facility_id=facility_id,
                        appointment_id=appointment_id,  # duplicate
                        visit_date=datetime.now(timezone.utc),
                        status=VisitStatus.DRAFT.value,
                    )
                )
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id],
            facility_ids=[facility_id],
        )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for visits PostgreSQL coverage",
)
def test_postgresql_status_check_constraint_rejects_unknown_values() -> None:
    """The CHECK(status IN ('DRAFT','FINALIZED')) ensures callers
    cannot persist bogus statuses directly through the ORM.
    """

    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    (
        doctor_user_id,
        registration_id,
        facility_id,
        _session_id,
        appointment_id,
        _queue_entry_id,
        citizen_profile_id,
    ) = _seed_visits_fixture(engine)

    try:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    MedicalVisit.__table__.insert().values(
                        id=uuid.uuid4(),
                        citizen_id=citizen_profile_id,
                        doctor_role_registration_id=registration_id,
                        facility_id=facility_id,
                        appointment_id=appointment_id,
                        visit_date=datetime.now(timezone.utc),
                        status="OBSOLETE",
                    )
                )
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id],
            facility_ids=[facility_id],
        )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for visits PostgreSQL coverage",
)
def test_postgresql_update_to_finalized_persists_changed_status() -> None:
    """A real UPDATE that flips status from DRAFT to FINALIZED must
    succeed and be visible to subsequent SELECTs.
    """

    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    (
        doctor_user_id,
        registration_id,
        facility_id,
        _session_id,
        appointment_id,
        _queue_entry_id,
        citizen_profile_id,
    ) = _seed_visits_fixture(engine)

    visit_id = uuid.uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(
                MedicalVisit.__table__.insert().values(
                    id=visit_id,
                    citizen_id=citizen_profile_id,
                    doctor_role_registration_id=registration_id,
                    facility_id=facility_id,
                    appointment_id=appointment_id,
                    visit_date=datetime.now(timezone.utc),
                    status=VisitStatus.DRAFT.value,
                    clinical_notes="Initial notes",
                )
            )

        with Session(engine) as session:
            visit = session.get(MedicalVisit, visit_id)
            assert visit is not None
            assert visit.status == VisitStatus.DRAFT.value
            visit.status = VisitStatus.FINALIZED.value
            visit.finalized_at = datetime.now(timezone.utc)
            session.commit()

        with Session(engine) as session:
            refreshed = session.get(MedicalVisit, visit_id)
            assert refreshed is not None
            assert refreshed.status == VisitStatus.FINALIZED.value
            assert refreshed.finalized_at is not None
            assert refreshed.clinical_notes == "Initial notes"
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id],
            facility_ids=[facility_id],
        )