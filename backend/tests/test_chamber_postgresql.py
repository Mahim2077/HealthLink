from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timezone
from threading import Barrier

import pytest
from sqlalchemy import and_, delete, func, select, text
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
from app.appointments.service import AppointmentService
from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
from app.auth.models import AuthSession, User
from app.citizens.models import CitizenProfile, UserNationalIdentifier
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_database_engine
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
from app.professionals.dependencies import ProfessionalAuthContext
from app.visits.models import MedicalVisit, VisitStatus


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


def _seed_chamber_fixture(
    engine,
    *,
    max_patients: int = 8,
    seed_appointments: int = 4,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Seed a doctor, facility, schedule, practice session, and ``seed_appointments``
    BOOKED appointments with queue entries in WAITING.

    Returns ``(doctor_user_id, registration_id, facility_id, session_id,
    citizen_user_id, citizen_profile_id)``.
    """

    facility_id = uuid.uuid4()
    doctor_user_id = uuid.uuid4()
    registration_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    schedule_id = uuid.uuid4()
    session_id = uuid.uuid4()
    citizen_user_id = uuid.uuid4()
    citizen_profile_id = uuid.uuid4()

    today = date.today()
    while today.strftime("%A").upper() != "MONDAY":
        today = today.fromordinal(today.toordinal() + 1)

    with engine.begin() as connection:
        connection.execute(
            HealthcareFacility.__table__.insert().values(
                id=facility_id,
                name="PG Chamber Facility",
                facility_type="HOSPITAL",
                registration_number=f"REG-{uuid.uuid4().hex[:8]}",
                address="Dhaka",
                phone="+8801700000000",
                email="pg-chamber@example.com",
                is_active=True,
            )
        )
        connection.execute(
            User.__table__.insert().values(
                id=doctor_user_id,
                email=f"pg-chamber-doctor-{doctor_user_id.hex[:8]}@example.com",
                password_hash="pg-chamber-hash",
                first_name="PG",
                last_name="ChamberDoctor",
            )
        )
        connection.execute(
            User.__table__.insert().values(
                id=citizen_user_id,
                email=f"pg-chamber-citizen-{citizen_user_id.hex[:8]}@example.com",
                password_hash="pg-chamber-hash",
                first_name="PG",
                last_name="ChamberCitizen",
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
                facility_name_submitted="PG Chamber Facility",
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
        for index in range(seed_appointments):
            appointment_id = uuid.uuid4()
            queue_entry_id = uuid.uuid4()
            connection.execute(
                Appointment.__table__.insert().values(
                    id=appointment_id,
                    citizen_id=citizen_profile_id,
                    doctor_role_registration_id=registration_id,
                    facility_id=facility_id,
                    appointment_date=today,
                    serial_number=index + 1,
                    status=AppointmentStatus.BOOKED.value,
                    booked_at=datetime.now(timezone.utc),
                )
            )
            connection.execute(
                AppointmentQueueEntry.__table__.insert().values(
                    id=queue_entry_id,
                    appointment_id=appointment_id,
                    practice_session_id=session_id,
                    queue_status=QueueStatus.WAITING.value,
                )
            )

    return (
        doctor_user_id,
        registration_id,
        facility_id,
        session_id,
        citizen_user_id,
        citizen_profile_id,
    )


def _cleanup(
    engine,
    *,
    user_ids: list[uuid.UUID],
    facility_ids: list[uuid.UUID],
) -> None:
    """Tear down the seeded chamber fixture in dependency order."""

    with engine.begin() as connection:
        if facility_ids:
            connection.execute(
                delete(DoctorPracticeSchedule).where(
                    DoctorPracticeSchedule.facility_id.in_(facility_ids)
                )
            )
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
                delete(MedicalVisit).where(
                    MedicalVisit.appointment_id.in_(
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
        if user_ids:
            citizen_profile_ids = select(CitizenProfile.id).where(
                CitizenProfile.user_id.in_(user_ids)
            )
            connection.execute(
                delete(AuthSession).where(AuthSession.user_id.in_(user_ids))
            )
            connection.execute(
                delete(DoctorPracticeSchedule).where(
                    DoctorPracticeSchedule.doctor_user_id.in_(user_ids)
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
                delete(ProfessionalRoleRegistration).where(
                    ProfessionalRoleRegistration.facility_id.in_(facility_ids)
                )
            )
            connection.execute(
                delete(HealthcareFacility).where(
                    HealthcareFacility.id.in_(facility_ids)
                )
            )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for chamber PostgreSQL coverage",
)
def test_postgresql_partial_unique_index_blocks_second_current_queue_entry() -> None:
    """Even with the advisory lock, the partial unique index is the
    ultimate safety net. Two CURRENT rows for the same session must fail.
    """

    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    _, _, facility_id, session_id, doctor_user_id, citizen_user_id = (
        _seed_chamber_fixture(engine, max_patients=4, seed_appointments=2)
    )

    try:
        with Session(engine) as session:
            # Select the lowest WAITING serial first, then update by ID.
            # This mirrors the production call-next path and is the only
            # safe way to promote exactly one row when the partial unique
            # index forbids two CURRENT rows for the same session — a
            # multi-row UPDATE without LIMIT would immediately fail.
            next_waiting_id = session.scalar(
                select(AppointmentQueueEntry.id)
                .join(
                    Appointment,
                    Appointment.id == AppointmentQueueEntry.appointment_id,
                )
                .where(
                    AppointmentQueueEntry.practice_session_id == session_id,
                    AppointmentQueueEntry.queue_status == QueueStatus.WAITING.value,
                )
                .order_by(Appointment.serial_number.asc())
                .limit(1)
            )
            assert next_waiting_id is not None
            session.execute(
                AppointmentQueueEntry.__table__.update()
                .where(AppointmentQueueEntry.id == next_waiting_id)
                .values(
                    queue_status=QueueStatus.CURRENT.value,
                    became_current_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

        # A second CURRENT row in the same session must be rejected by the
        # partial unique index added in migration 0018. We mirror the same
        # select-then-update pattern so the only thing under test is the
        # index behavior, not statement shape.
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                next_waiting_id = connection.execute(
                    select(AppointmentQueueEntry.id)
                    .join(
                        Appointment,
                        Appointment.id == AppointmentQueueEntry.appointment_id,
                    )
                    .where(
                        AppointmentQueueEntry.practice_session_id == session_id,
                        AppointmentQueueEntry.queue_status
                        == QueueStatus.WAITING.value,
                    )
                    .order_by(Appointment.serial_number.asc())
                    .limit(1)
                ).scalar()
                assert next_waiting_id is not None
                connection.execute(
                    AppointmentQueueEntry.__table__.update()
                    .where(AppointmentQueueEntry.id == next_waiting_id)
                    .values(
                        queue_status=QueueStatus.CURRENT.value,
                        became_current_at=datetime.now(timezone.utc),
                    )
                )
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id, citizen_user_id],
            facility_ids=[facility_id],
        )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for chamber PostgreSQL coverage",
)
def test_postgresql_appointment_cancellation_excludes_from_chamber_view() -> None:
    """Canceling a BOOKED appointment while it is WAITING must remove it from
    the chamber waiting list (existing partial-session invariant).
    """

    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    _, _, facility_id, session_id, doctor_user_id, citizen_user_id = (
        _seed_chamber_fixture(engine, max_patients=4, seed_appointments=3)
    )

    try:
        # Cancel the highest-serial appointment directly.
        with engine.begin() as connection:
            target = connection.execute(
                select(Appointment).where(
                    Appointment.facility_id == facility_id,
                    Appointment.serial_number == 3,
                )
            ).first()
            assert target is not None
            connection.execute(
                Appointment.__table__.update()
                .where(Appointment.id == target.id)
                .values(
                    status=AppointmentStatus.CANCELLED.value,
                    cancelled_at=datetime.now(timezone.utc),
                )
            )

        # Now the chamber query should only see serials 1 and 2 as WAITING.
        with Session(engine) as session:
            entries = session.scalars(
                select(AppointmentQueueEntry)
                .join(
                    Appointment,
                    Appointment.id == AppointmentQueueEntry.appointment_id,
                )
                .where(
                    AppointmentQueueEntry.practice_session_id == session_id,
                    AppointmentQueueEntry.queue_status == QueueStatus.WAITING.value,
                    Appointment.status == AppointmentStatus.BOOKED.value,
                )
                .order_by(Appointment.serial_number.asc())
            ).all()
            assert len(entries) == 2
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id, citizen_user_id],
            facility_ids=[facility_id],
        )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for chamber PostgreSQL coverage",
)
def test_postgresql_concurrent_promote_keeps_single_current() -> None:
    """Two threads racing to promote WAITING -> CURRENT must end up with
    exactly one CURRENT row per session, courtesy of the advisory lock
    plus the partial unique index.

    Uses the repository's lock helper directly because the SQL pattern
    is what we want to validate under contention.
    """

    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(
        POSTGRES_TEST_DATABASE_URL,
        poolclass=NullPool,
        disable_prepared_statements=True,
    )
    Base.metadata.create_all(engine)

    _, registration_id, facility_id, session_id, doctor_user_id, citizen_user_id = (
        _seed_chamber_fixture(engine, max_patients=8, seed_appointments=4)
    )

    target_date = None
    with engine.begin() as connection:
        session_row = connection.execute(
            select(DoctorPracticeSession).where(
                DoctorPracticeSession.id == session_id
            )
        ).first()
        target_date = session_row.session_date

    try:
        # The barrier must be reached BEFORE either thread takes the
        # advisory lock — otherwise thread A acquires the lock, blocks on
        # barrier.wait() waiting for thread B, but thread B can never
        # acquire the lock because thread A holds it. Classic deadlock.
        # Using `parties=2` plus the lock makes the race window tiny in
        # practice, but we don't rely on timing — we ensure both threads
        # are past the barrier before either touches the lock.
        barrier = Barrier(2)
        outcomes: list[tuple[bool, str]] = []

        def _promote() -> None:
            """Synchronize both threads at the barrier, then race to take
            the queue lock and promote the lowest WAITING serial in this
            session to CURRENT. The promotion uses select-then-update-by-
            ID so the partial unique index on (session, CURRENT) provides
            a final safety net beyond the advisory lock.
            """

            from app.appointments.repository import AppointmentRepository

            with Session(engine, expire_on_commit=False) as session:
                repository = AppointmentRepository(session)
                try:
                    # Synchronize: both threads must be ready to race
                    # before either takes the advisory lock.
                    barrier.wait()

                    repository._lock_for_queue(
                        doctor_role_registration_id=registration_id,
                        session_date=target_date,
                    )

                    next_waiting_id = session.scalar(
                        select(AppointmentQueueEntry.id)
                        .join(
                            Appointment,
                            Appointment.id == AppointmentQueueEntry.appointment_id,
                        )
                        .where(
                            and_(
                                AppointmentQueueEntry.practice_session_id
                                == session_id,
                                AppointmentQueueEntry.queue_status
                                == QueueStatus.WAITING.value,
                                Appointment.status == AppointmentStatus.BOOKED.value,
                            )
                        )
                        .order_by(Appointment.serial_number.asc())
                        .limit(1)
                    )
                    if next_waiting_id is None:
                        session.rollback()
                        outcomes.append((True, "no-waiting"))
                        return

                    session.execute(
                        AppointmentQueueEntry.__table__.update()
                        .where(AppointmentQueueEntry.id == next_waiting_id)
                        .values(
                            queue_status=QueueStatus.CURRENT.value,
                            became_current_at=func.now(),
                        )
                    )
                    session.commit()
                    outcomes.append((True, ""))
                except IntegrityError:
                    session.rollback()
                    outcomes.append((False, "integrity"))
                except Exception as error:  # pragma: no cover - defensive
                    session.rollback()
                    outcomes.append((False, repr(error)))

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(_promote) for _ in range(2)]
            for future in futures:
                future.result()

        # At least one thread must have promoted; the other must have lost
        # the race (either via the lock or the partial unique index).
        assert any(result[0] for result in outcomes), outcomes

        with Session(engine) as session:
            current_rows = session.scalars(
                select(AppointmentQueueEntry).where(
                    AppointmentQueueEntry.practice_session_id == session_id,
                    AppointmentQueueEntry.queue_status == QueueStatus.CURRENT.value,
                )
            ).all()
            assert len(current_rows) == 1
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id, citizen_user_id],
            facility_ids=[facility_id],
        )


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for finish concurrency coverage",
)
def test_postgresql_concurrent_finish_is_idempotent_and_advances_once() -> None:
    """Concurrent finish retries serialize and never skip serial 2."""

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
        session_id,
        citizen_user_id,
        citizen_profile_id,
    ) = _seed_chamber_fixture(
        engine,
        max_patients=4,
        seed_appointments=3,
    )

    visit_id = uuid.uuid4()
    appointment_id: uuid.UUID | None = None
    queue_id: uuid.UUID | None = None
    with engine.begin() as connection:
        first = connection.execute(
            select(Appointment.id, AppointmentQueueEntry.id)
            .join(
                AppointmentQueueEntry,
                AppointmentQueueEntry.appointment_id == Appointment.id,
            )
            .where(
                AppointmentQueueEntry.practice_session_id == session_id
            )
            .order_by(Appointment.serial_number.asc())
            .limit(1)
        ).one()
        appointment_id, queue_id = first
        connection.execute(
            AppointmentQueueEntry.__table__.update()
            .where(AppointmentQueueEntry.id == queue_id)
            .values(
                queue_status=QueueStatus.CURRENT.value,
                became_current_at=datetime.now(timezone.utc),
            )
        )
        connection.execute(
            MedicalVisit.__table__.insert().values(
                id=visit_id,
                citizen_id=citizen_profile_id,
                doctor_role_registration_id=registration_id,
                facility_id=facility_id,
                appointment_id=appointment_id,
                status=VisitStatus.DRAFT.value,
            )
        )
    assert appointment_id is not None
    assert queue_id is not None

    settings = Settings(
        _env_file=None,
        app_name="HealthLink Finish Concurrency Test",
        app_env="test",
        debug=False,
        database_url=POSTGRES_TEST_DATABASE_URL,
        frontend_url="http://localhost:3000",
        jwt_secret_key="phase-14-concurrency-secret-at-least-32-characters",
    )
    barrier = Barrier(2, timeout=15)
    outcomes: list[tuple[bool, int | str]] = []

    def _finish() -> None:
        try:
            # Synchronize before either worker opens a transaction. A bounded
            # barrier plus database-side timeouts makes a CI regression fail
            # diagnostically instead of leaving the runner blocked forever.
            barrier.wait()
            with Session(engine, expire_on_commit=False) as session:
                session.execute(text("SET LOCAL lock_timeout = '10s'"))
                session.execute(text("SET LOCAL statement_timeout = '30s'"))
                registration = session.get(
                    ProfessionalRoleRegistration,
                    registration_id,
                )
                assert registration is not None
                context = ProfessionalAuthContext(
                    auth=None,  # type: ignore[arg-type] - service uses role only.
                    role_registration=registration,
                )
                response = AppointmentService(
                    session,
                    settings,
                ).finish_appointment(context, appointment_id)
                outcomes.append(
                    (
                        True,
                        response.next_current.serial_number
                        if response.next_current is not None
                        else "none",
                    )
                )
        except Exception as error:  # pragma: no cover - assertion reports.
            outcomes.append((False, repr(error)))

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(_finish) for _ in range(2)]
            for future in futures:
                future.result(timeout=45)

        assert len(outcomes) == 2
        assert all(outcome == (True, 2) for outcome in outcomes), outcomes

        with Session(engine) as session:
            appointment = session.get(Appointment, appointment_id)
            visit = session.get(MedicalVisit, visit_id)
            finished_entry = session.get(AppointmentQueueEntry, queue_id)
            assert appointment.status == AppointmentStatus.COMPLETED.value
            assert visit.status == VisitStatus.FINALIZED.value
            assert finished_entry.queue_status == QueueStatus.DONE.value

            rows = session.execute(
                select(
                    Appointment.serial_number,
                    AppointmentQueueEntry.queue_status,
                )
                .join(
                    AppointmentQueueEntry,
                    AppointmentQueueEntry.appointment_id == Appointment.id,
                )
                .where(
                    AppointmentQueueEntry.practice_session_id == session_id
                )
                .order_by(Appointment.serial_number.asc())
            ).all()
            assert rows == [
                (1, QueueStatus.DONE.value),
                (2, QueueStatus.CURRENT.value),
                (3, QueueStatus.WAITING.value),
            ]
    finally:
        _cleanup(
            engine,
            user_ids=[doctor_user_id, citizen_user_id],
            facility_ids=[facility_id],
        )
