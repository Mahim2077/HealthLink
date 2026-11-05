"""Accepted secondary-facility bookings must remain serviceable and isolated."""
from datetime import date, timedelta
import uuid

import pytest
from sqlalchemy import func, select

from app.appointments.models import Appointment, AppointmentQueueEntry, DoctorPracticeSession
from test_chamber import _book, _login_professional, _start_session
from test_prescriptions import (
    _VALID_PAYLOAD, _add_schedule, _make_facility, _make_verified_doctor, _register_citizen,
)

BASE = "/api/v1/professionals/chamber"
CURRENT = "/api/v1/doctors/me/visits/current-patient"


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def setup_chambers(client, db, day_offset=0):
    primary = _make_facility(db, name="Primary care facility")
    secondary = _make_facility(db, name="Secondary care facility")
    doctor, registration, nid, password = _make_verified_doctor(
        db, first_name="Multi", last_name="Facility", facility=primary,
        nid_number=f"NID-{uuid.uuid4().hex[:20]}", bmdc=f"BMDC-{uuid.uuid4().hex}",
    )
    token = _login_professional(client, nid_number=nid, password=password)
    first_date, second_date = date.today(), date.today() + timedelta(days=day_offset)
    schedules, bookings, citizens = [], [], []
    for facility, target in ((primary, first_date), (secondary, second_date)):
        schedules.append(_add_schedule(db, doctor_user_id=doctor, facility=facility,
            weekday=target.strftime("%A").upper()))
        citizen_token, _ = _register_citizen(client)
        citizens.append(citizen_token)
        bookings.append(_book(client, citizen_token, doctor_user_id=doctor,
            facility_id=facility.id, appointment_date=target))
    return primary, secondary, token, bookings, citizens, schedules, second_date


def test_secondary_care_finishes_and_publishes_the_correct_facility(client, db_session):
    primary, secondary, token, bookings, citizens, _, target = setup_chambers(client, db_session)
    choices = client.get(f"{BASE}/facilities", headers=headers(token))
    assert choices.status_code == 200
    assert choices.json() == [{"id": str(primary.id), "name": primary.name},
                              {"id": str(secondary.id), "name": secondary.name}]
    # Empty primary chamber must not hide the selected secondary patient's queue.
    primary_session = db_session.scalar(select(DoctorPracticeSession).where(
        DoctorPracticeSession.facility_id == primary.id))
    assert primary_session.status == "NOT_STARTED"
    started = _start_session(client, token, facility_id=secondary.id, session_date=target)
    assert started["current"]["appointment_id"] == bookings[1]["id"]
    viewed = client.get(f"{BASE}/sessions/today", headers=headers(token),
        params={"facility_id": str(secondary.id), "session_date": target.isoformat()})
    assert viewed.status_code == 200
    current = client.get(CURRENT, headers=headers(token))
    assert current.status_code == 200
    assert current.json()["facility_id"] == str(secondary.id)
    assert current.json()["appointment_id"] == bookings[1]["id"]
    queue_id = started["current"]["queue_id"]
    visit = client.post(f"/api/v1/doctors/me/visits/start-for-current/{queue_id}", headers=headers(token))
    assert visit.status_code == 200, visit.text
    assert visit.json()["facility_id"] == str(secondary.id)
    prescription = client.post(f"/api/v1/visits/{visit.json()['id']}/prescription",
        headers=headers(token), json=_VALID_PAYLOAD)
    assert prescription.status_code == 201, prescription.text
    path = f"/api/v1/prescriptions/{prescription.json()['id']}"
    assert client.get(path, headers=headers(citizens[1])).status_code == 404
    assert client.get(path, headers=headers(citizens[0])).status_code == 404
    finished = client.post(f"/api/v1/appointments/{bookings[1]['id']}/finish", headers=headers(token))
    assert finished.status_code == 200, finished.text
    published = client.get(path, headers=headers(citizens[1]))
    assert published.status_code == 200, published.text
    assert published.json()["visit_id"] == visit.json()["id"]
    citizen_visit = client.get(f"/api/v1/citizens/me/visits/{visit.json()['id']}", headers=headers(citizens[1]))
    assert citizen_visit.status_code == 200
    assert citizen_visit.json()["facility_id"] == str(secondary.id)
    assert client.get(path, headers=headers(citizens[0])).status_code == 404
    pdf = client.get(path + "/pdf", headers=headers(citizens[1]))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert client.get(CURRENT, headers=headers(token)).json() is None
    # Primary queue retains its own waiting booking and can continue afterward.
    first = _start_session(client, token, facility_id=primary.id, session_date=date.today())
    assert first["current"]["appointment_id"] == bookings[0]["id"]


def test_foreign_doctor_facilities_and_queue_actions_stay_denied(client, db_session):
    primary, secondary, token, bookings, citizens, _, target = setup_chambers(client, db_session)
    foreign = _make_facility(db_session, name="Unrelated practice")
    doctor, _, nid, password = _make_verified_doctor(db_session, first_name="Other", last_name="Doctor",
        facility=foreign, nid_number=f"NID-{uuid.uuid4().hex[:20]}")
    _add_schedule(db_session, doctor_user_id=doctor, facility=foreign, weekday=target.strftime("%A").upper())
    other = _login_professional(client, nid_number=nid, password=password)
    assert str(foreign.id) not in {row["id"] for row in client.get(f"{BASE}/facilities", headers=headers(token)).json()}
    assert client.get(f"{BASE}/facilities", headers=headers(citizens[0])).status_code == 403
    assert client.get(f"{BASE}/facilities").status_code == 401
    for facility, actor in ((foreign, token), (secondary, other)):
        payload = {"facility_id": str(facility.id), "session_date": target.isoformat()}
        assert client.get(f"{BASE}/sessions/today", headers=headers(actor), params=payload).status_code == 409
        assert client.post(f"{BASE}/sessions/start", headers=headers(actor), json=payload).status_code == 409
    opened = _start_session(client, token, facility_id=secondary.id, session_date=target)
    queue_id = opened["current"]["queue_id"]
    assert client.post(f"{BASE}/queue/{queue_id}/skip", headers=headers(other)).status_code == 404
    assert client.post(f"/api/v1/doctors/me/visits/start-for-current/{queue_id}", headers=headers(other)).status_code == 404
    assert client.post(f"/api/v1/appointments/{bookings[1]['id']}/finish", headers=headers(other)).status_code == 404


def test_retiring_a_schedule_preserves_accepted_secondary_bookings(client, db_session):
    _, secondary, token, bookings, _, schedules, target = setup_chambers(client, db_session)
    retired = client.delete(f"/api/v1/professionals/me/practice-schedule/{schedules[1].id}", headers=headers(token))
    assert retired.status_code == 200 and retired.json()["deleted_at"]
    choices = client.get(f"{BASE}/facilities", headers=headers(token)).json()
    assert str(secondary.id) in {row["id"] for row in choices}
    opened = _start_session(client, token, facility_id=secondary.id, session_date=target)
    assert opened["current"]["appointment_id"] == bookings[1]["id"]


def test_retired_unbooked_practice_disappears_from_chamber_choices(client, db_session):
    _, _, token, _, _, _, target = setup_chambers(client, db_session)
    unused = _make_facility(db_session, name="Unused retired practice")
    created = client.post("/api/v1/professionals/me/practice-schedule", headers=headers(token),
        json={"facility_id": str(unused.id), "weekday": target.strftime("%A").upper(),
              "start_time": "09:00", "end_time": "11:00", "max_patients": 5, "status": "ACTIVE"})
    assert created.status_code == 201, created.text
    assert str(unused.id) in {row["id"] for row in client.get(f"{BASE}/facilities", headers=headers(token)).json()}
    retired = client.delete(f"/api/v1/professionals/me/practice-schedule/{created.json()['schedule']['id']}", headers=headers(token))
    assert retired.status_code == 200 and retired.json()["deleted_at"]
    assert str(unused.id) not in {row["id"] for row in client.get(f"{BASE}/facilities", headers=headers(token)).json()}


def test_closed_chamber_rejects_bookings_without_consuming_rows_or_serials(client, db_session):
    primary, secondary, token, bookings, _, _, target = setup_chambers(client, db_session)
    _start_session(client, token, facility_id=primary.id, session_date=target)
    closed = client.post(f"{BASE}/sessions/finish", headers=headers(token),
        params={"facility_id": str(primary.id), "session_date": target.isoformat()})
    assert closed.status_code == 200, closed.text
    citizen, _ = _register_citizen(client)
    before = tuple(db_session.scalar(select(func.count(model.id))) for model in (Appointment, AppointmentQueueEntry))
    payload = {"doctor_user_id": bookings[0]["doctor_user_id"], "facility_id": str(primary.id),
               "appointment_date": target.isoformat()}
    for _ in range(2):
        rejected = client.post("/api/v1/citizens/appointments", headers=headers(citizen), json=payload)
        assert rejected.status_code == 409, rejected.text
        assert "Choose another available date" in rejected.json()["detail"]
    assert tuple(db_session.scalar(select(func.count(model.id))) for model in (Appointment, AppointmentQueueEntry)) == before
    assert db_session.scalar(select(func.max(Appointment.serial_number)).where(
        Appointment.facility_id == primary.id, Appointment.appointment_date == target)) == 1
    future = client.post("/api/v1/citizens/appointments", headers=headers(citizen),
        json={**payload, "appointment_date": (target + timedelta(days=7)).isoformat()})
    assert future.status_code == 201 and future.json()["serial_number"] == 1
    elsewhere = client.post("/api/v1/citizens/appointments", headers=headers(citizen),
        json={**payload, "facility_id": str(secondary.id)})
    assert elsewhere.status_code == 201 and elsewhere.json()["serial_number"] == 2


@pytest.mark.parametrize("day_offset", [0, 7])
def test_only_one_current_patient_across_facilities_and_dates(client, db_session, day_offset):
    primary, secondary, token, bookings, _, _, target = setup_chambers(client, db_session, day_offset)
    first = _start_session(client, token, facility_id=primary.id, session_date=date.today())
    blocked = client.post(f"{BASE}/sessions/start", headers=headers(token),
        json={"facility_id": str(secondary.id), "session_date": target.isoformat()})
    assert blocked.status_code == 409, blocked.text
    assert "other chamber" in blocked.json()["detail"]
    session = db_session.scalar(select(DoctorPracticeSession).where(DoctorPracticeSession.facility_id == secondary.id))
    assert session.status == "NOT_STARTED"
    assert client.get(CURRENT, headers=headers(token)).json()["appointment_id"] == bookings[0]["id"]
    skipped = client.post(f"{BASE}/queue/{first['current']['queue_id']}/skip", headers=headers(token))
    assert skipped.status_code == 200, skipped.text
    second = _start_session(client, token, facility_id=secondary.id, session_date=target)
    assert second["current"]["appointment_id"] == bookings[1]["id"]
    assert client.get(CURRENT, headers=headers(token)).json()["facility_id"] == str(secondary.id)


def test_legacy_ambiguous_current_patients_fail_closed(client, db_session):
    primary, secondary, token, bookings, _, _, target = setup_chambers(client, db_session)
    _start_session(client, token, facility_id=primary.id, session_date=target)
    second_session = db_session.scalar(select(DoctorPracticeSession).where(DoctorPracticeSession.facility_id == secondary.id))
    second_entry = db_session.get(AppointmentQueueEntry, uuid.UUID(bookings[1]["queue"]["id"]))
    second_session.status, second_entry.queue_status = "ACTIVE", "CURRENT"
    db_session.commit()
    response = client.get(CURRENT, headers=headers(token))
    assert response.status_code == 409
    assert "More than one chamber" in response.json()["detail"]
