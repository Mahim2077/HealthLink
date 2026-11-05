"""Real PostgreSQL races must not select two current patients for one Doctor."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.appointments.models import Appointment, AppointmentQueueEntry, DoctorPracticeSession
from app.appointments.schemas import AppointmentBookingRequest
from app.appointments.service import AppointmentService, AppointmentScheduleUnavailableError, ChamberQueueStateError
from app.db.session import create_database_engine
from app.facilities.models import HealthcareFacility
from app.professionals.models import ProfessionalRoleRegistration
from test_chamber_postgresql import POSTGRES_TEST_DATABASE_URL, _cleanup, _seed_chamber_fixture


@pytest.mark.skipif(not POSTGRES_TEST_DATABASE_URL, reason="Dedicated PostgreSQL URL required")
@pytest.mark.parametrize("day_offset", [0, 7])
def test_simultaneous_facility_starts_keep_one_current_patient(test_settings, day_offset):
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    doctor, registration_id, primary, session_id, citizen, citizen_profile = _seed_chamber_fixture(engine)
    secondary_id = uuid.uuid4()
    try:
        with Session(engine) as db:
            original = db.get(DoctorPracticeSession, session_id)
            first_date = original.session_date
            second_date = first_date + timedelta(days=day_offset)
            secondary = HealthcareFacility(id=secondary_id, name="Concurrent secondary facility", facility_type="HOSPITAL",
                registration_number=f"REG-{uuid.uuid4()}", address="Synthetic test", phone="01000000000", is_active=True)
            db.add(secondary)
            db.flush()
            session = DoctorPracticeSession(doctor_role_registration_id=registration_id, facility_id=secondary_id,
                session_date=second_date, status="NOT_STARTED")
            db.add(session)
            db.flush()
            appointment = Appointment(citizen_id=citizen_profile, doctor_role_registration_id=registration_id,
                facility_id=secondary_id, appointment_date=second_date, serial_number=1, status="BOOKED",
                booked_at=datetime.now(UTC))
            db.add(appointment)
            db.flush()
            db.add(AppointmentQueueEntry(appointment_id=appointment.id, practice_session_id=session.id, queue_status="WAITING"))
            db.commit()
        barrier = Barrier(2)

        def start(facility, target):
            with Session(engine) as db:
                registration = db.get(ProfessionalRoleRegistration, registration_id)
                barrier.wait(timeout=15)
                try:
                    view = AppointmentService(db, test_settings).start_session(
                        SimpleNamespace(role_registration=registration), facility_id=facility, session_date=target)
                    assert view.current is not None
                    return "started"
                except ChamberQueueStateError as error:
                    assert "other chamber" in error.detail
                    return "blocked"

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(start, primary, first_date), executor.submit(start, secondary_id, second_date)]
            outcomes = [future.result(timeout=30) for future in futures]
        assert sorted(outcomes) == ["blocked", "started"]
        with Session(engine) as db:
            current = list(db.scalars(select(AppointmentQueueEntry)
                .join(DoctorPracticeSession, DoctorPracticeSession.id == AppointmentQueueEntry.practice_session_id)
                .where(DoctorPracticeSession.doctor_role_registration_id == registration_id,
                       AppointmentQueueEntry.queue_status == "CURRENT")))
            assert len(current) == 1
    finally:
        _cleanup(engine, user_ids=[doctor, citizen], facility_ids=[primary, secondary_id])
        engine.dispose()


@pytest.mark.skipif(not POSTGRES_TEST_DATABASE_URL, reason="Dedicated PostgreSQL URL required")
@pytest.mark.parametrize("first_action", ["close", "book"])
def test_booking_and_closure_serialize_in_both_orders(test_settings, first_action):
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    doctor, registration_id, facility, session_id, citizen, _ = _seed_chamber_fixture(engine, seed_appointments=0)
    ready = Event()
    try:
        with Session(engine) as db:
            target = db.get(DoctorPracticeSession, session_id).session_date
        payload = AppointmentBookingRequest(doctor_user_id=doctor, facility_id=facility, appointment_date=target)

        def perform(db, action):
            service = AppointmentService(db, test_settings)
            if action == "book":
                try:
                    service.book_appointment(citizen, payload)
                    return "booked"
                except AppointmentScheduleUnavailableError as error:
                    assert "closed this chamber" in error.detail
                    db.rollback()
                    return "rejected"
            service.finish_session(SimpleNamespace(role_registration=db.get(ProfessionalRoleRegistration, registration_id)),
                facility_id=facility, session_date=target)
            return "closed"

        def second_action():
            with Session(engine) as db:
                # Exercise stale identity-map state as well as actual lock contention.
                _cached_session = db.get(DoctorPracticeSession, session_id)
                ready.set()
                return perform(db, "book" if first_action == "close" else "close")

        with ThreadPoolExecutor(max_workers=1) as executor:
            with Session(engine) as first_db:
                service = AppointmentService(first_db, test_settings)
                if first_action == "book":
                    service.repository._lock_for_booking(registration_id, target)
                service.repository._lock_for_queue(registration_id, target)
                future = executor.submit(second_action)
                try:
                    assert ready.wait(timeout=15)
                    with pytest.raises(TimeoutError):
                        future.result(timeout=0.3)
                    first_result = perform(first_db, first_action)
                finally:
                    first_db.rollback()
            second_result = future.result(timeout=30)
        assert (first_result, second_result) == (("closed", "rejected") if first_action == "close" else ("booked", "closed"))
        with Session(engine) as db:
            session = db.get(DoctorPracticeSession, session_id)
            assert session.status == "COMPLETED"
            appointments = list(db.scalars(select(Appointment).where(Appointment.facility_id == facility)))
            queues = list(db.scalars(select(AppointmentQueueEntry).where(AppointmentQueueEntry.practice_session_id == session_id)))
            assert len(appointments) == len(queues) == (0 if first_action == "close" else 1)
            if appointments:
                assert appointments[0].booked_at <= session.ended_at
    finally:
        _cleanup(engine, user_ids=[doctor, citizen], facility_ids=[facility])
        engine.dispose()
