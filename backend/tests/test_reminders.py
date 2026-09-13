import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta
from threading import Barrier

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.auth.constants import Portal
from app.core.config import get_settings
from app.db.base import Base
from app.prescriptions.models import Prescription, PrescriptionItem
from app.professionals.constants import ProfessionalRoleCode
from app.reminders.models import MedicineReminder, MedicineReminderTime, Notification
from app.reminders.schemas import ReminderInput
from app.reminders.service import ReminderService
from test_diagnostics import _auth, _citizen, _facility, _queue, _registration, _token
from test_diagnostics_postgresql import diagnostic_pg_engine  # noqa: F401


def _payload(**overrides):
    return {"medicine": "Medicine A", "start_date": "2026-09-12", "times": ["08:00", "20:00"], **overrides}


def _seed_due(db):
    _, citizen = _citizen(db, "Reminder")
    row = MedicineReminder(citizen_id=citizen.id, medicine="Medicine A", start_date=date(2026, 9, 10), schedule_updated_at=datetime(2026, 9, 10, tzinfo=UTC))
    db.add(row); db.flush()
    db.add_all([MedicineReminderTime(reminder_id=row.id, daily_time=time(8)), MedicineReminderTime(reminder_id=row.id, daily_time=time(20))]); db.commit()
    return citizen, row


def test_create_edit_activate_and_owner_boundaries(client, db_session, test_settings):
    user, citizen = _citizen(db_session, "Owner")
    other, _ = _citizen(db_session, "Other")
    headers = _auth(_token(db_session, test_settings, user, Portal.CITIZEN))
    foreign = _auth(_token(db_session, test_settings, other, Portal.CITIZEN))
    path = "/api/v1/citizens/me/reminders"
    created = client.post(path, headers=headers, json=_payload())
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    assert len(list(db_session.scalars(select(MedicineReminderTime)))) == 2
    assert client.get(path, headers=foreign).json() == []
    assert client.put(f"{path}/{rid}", headers=foreign, json=_payload()).status_code == 404
    assert client.put(f"{path}/{rid}/active", headers=foreign, json={"is_active": False}).status_code == 404
    edited = client.put(f"{path}/{rid}", headers=headers, json=_payload(medicine="Updated", times=["09:00"]))
    assert edited.status_code == 200
    assert edited.json()["medicine"] == "Updated"
    assert len(list(db_session.scalars(select(MedicineReminderTime)))) == 1
    assert client.put(f"{path}/{rid}/active", headers=headers, json={"is_active": False}).json()["is_active"] is False
    assert client.put(f"{path}/{rid}/active", headers=headers, json={"is_active": True}).json()["is_active"] is True
    assert client.post(path, json=_payload()).status_code == 401


@pytest.mark.parametrize("changes", [{"times": ["08:00", "08:00"]}, {"times": []}, {"times": ["08:00:01"]}, {"times": ["08:00:00+06:00"]}, {"end_date": "2026-09-11"}, {"timezone": "UTC"}, {"medicine": "  "}])
def test_invalid_schedules_rejected(changes):
    with pytest.raises(ValueError):
        ReminderInput(**_payload(**changes))


def test_prescription_link_requires_owned_finalized_matching_item(client, db_session, test_settings):
    facility = _facility(db_session)
    _, doctor = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    user, citizen = _citizen(db_session, "Owner")
    other, _ = _citizen(db_session, "Other")
    visit = _queue(db_session, doctor, facility, citizen)
    prescription = Prescription(visit_id=visit.id, citizen_id=citizen.id, author_doctor_role_registration_id=doctor.id)
    db_session.add(prescription); db_session.flush()
    item = PrescriptionItem(prescription_id=prescription.id, medicine_name="Medicine A", dosage="1", frequency="daily", duration="3 days")
    db_session.add(item); db_session.commit()
    headers = _auth(_token(db_session, test_settings, user, Portal.CITIZEN))
    payload = _payload(prescription_item_id=str(item.id))
    assert client.post("/api/v1/citizens/me/reminders", headers=headers, json=payload).status_code == 422
    visit.status = "FINALIZED"; visit.finalized_at = datetime.now(UTC); db_session.commit()
    assert client.post("/api/v1/citizens/me/reminders", headers=headers, json=payload).status_code == 201
    assert client.post("/api/v1/citizens/me/reminders", headers=headers, json={**payload, "medicine": "Mismatch"}).status_code == 422
    foreign = _auth(_token(db_session, test_settings, other, Portal.CITIZEN))
    assert client.post("/api/v1/citizens/me/reminders", headers=foreign, json=payload).status_code == 422
    assert client.get("/api/v1/citizens/me/reminder-prescription-items", headers=foreign).json() == []
    assert client.get("/api/v1/citizens/me/reminder-prescription-items", headers=headers).json()[0]["id"] == str(item.id)


def test_worker_local_times_date_bounds_retry_and_catchup(db_session):
    _, row = _seed_due(db_session)
    now = datetime(2026, 9, 12, 14, 1, tzinfo=UTC)  # 20:01 Dhaka
    service = ReminderService(db_session)
    assert service.run_due_reminders(now) == {"created": 2}
    assert service.run_due_reminders(now) == {"created": 0}
    notifications = list(db_session.scalars(select(Notification).order_by(Notification.due_at)))
    assert [n.due_at.replace(tzinfo=UTC).hour for n in notifications] == [2, 14]
    assert all("2026-09-12" in n.message for n in notifications)
    row.end_date = date(2026, 9, 12); db_session.commit()
    assert service.run_due_reminders(now + timedelta(days=1)) == {"created": 0}
    row.end_date = None; row.is_active = False; db_session.commit()
    assert service.run_due_reminders(now + timedelta(days=1)) == {"created": 0}
    row.is_active = True; row.schedule_updated_at = now + timedelta(days=1); db_session.commit()
    assert service.run_due_reminders(now + timedelta(days=1)) == {"created": 0}
    with pytest.raises(ValueError):
        service.run_due_reminders(datetime(2026, 9, 12))


def test_notification_read_acknowledgement_are_owned_and_idempotent(client, db_session, test_settings):
    user, citizen = _citizen(db_session, "Owner")
    other, _ = _citizen(db_session, "Other")
    notification = Notification(citizen_id=citizen.id, kind="MEDICINE", dedupe_key="test", message="Medicine reminder", due_at=datetime.now(UTC))
    db_session.add(notification); db_session.commit()
    base = f"/api/v1/citizens/me/notifications/{notification.id}"
    headers = _auth(_token(db_session, test_settings, user, Portal.CITIZEN))
    foreign = _auth(_token(db_session, test_settings, other, Portal.CITIZEN))
    assert client.get("/api/v1/citizens/me/notifications", headers=foreign).json() == []
    assert client.post(f"{base}/acknowledge", headers=foreign).status_code == 404
    first = client.post(f"{base}/read", headers=headers).json()
    assert first["read_at"] and first["acknowledged_at"] is None
    ack = client.post(f"{base}/acknowledge", headers=headers).json()
    assert ack["read_at"] == first["read_at"]
    assert ack["acknowledged_at"] == client.post(f"{base}/acknowledge", headers=headers).json()["acknowledged_at"]


def test_job_secret_fails_closed(client, test_settings):
    client.app.dependency_overrides[get_settings] = lambda: test_settings
    assert client.get("/api/v1/jobs/reminders").status_code == 503
    test_settings.cron_secret = "test-only-scheduler-secret"
    assert client.get("/api/v1/jobs/reminders").status_code == 401
    assert client.get("/api/v1/jobs/reminders", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/v1/jobs/reminders", headers={"Authorization": "Bearer test-only-scheduler-secret"}).json() == {"created": 0}


def test_reminder_cli_entrypoint_imports():
    from app.jobs.reminders import main
    assert callable(main)


def test_appointment_notice_is_serial_and_excludes_cancelled(db_session):
    facility = _facility(db_session)
    _, doctor = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    _, citizen = _citizen(db_session, "Appointment")
    appointment = Appointment(citizen_id=citizen.id, doctor_role_registration_id=doctor.id, facility_id=facility.id, appointment_date=date(2026, 9, 12), serial_number=7, status="BOOKED", booked_at=datetime(2026, 9, 11, tzinfo=UTC))
    db_session.add(appointment); db_session.commit()
    service = ReminderService(db_session)
    now = datetime(2026, 9, 12, 2, tzinfo=UTC)
    assert service.run_due_reminders(now)["created"] == 1
    text = db_session.scalar(select(Notification.message))
    assert "Serial 7" in text and facility.name in text and "2026-09-12" in text
    assert ":00" not in text and "queue position" in text
    assert service.run_due_reminders(now)["created"] == 0
    appointment.status = "CANCELLED"; db_session.execute(Notification.__table__.delete()); db_session.commit()
    assert service.run_due_reminders(now)["created"] == 0


def _concurrent_workers(engine):
    with Session(engine) as db:
        _seed_due(db)
    barrier = Barrier(2)
    def run():
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return ReminderService(db).run_due_reminders(datetime(2026, 9, 12, 14, 1, tzinfo=UTC))["created"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sum(results) == 2
    with Session(engine) as db:
        assert len(list(db.scalars(select(Notification)))) == 2


def test_concurrent_postgresql_workers_deduplicate(diagnostic_pg_engine):
    _concurrent_workers(diagnostic_pg_engine)


def test_concurrent_sqlite_workers_deduplicate(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'reminder-concurrency.sqlite'}", connect_args={"check_same_thread": False, "timeout": 15})
    Base.metadata.create_all(engine)
    try:
        _concurrent_workers(engine)
    finally:
        engine.dispose()
