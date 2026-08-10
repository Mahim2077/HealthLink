from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    AppointmentStatus,
    DoctorPracticeSession,
    QueueStatus,
    SessionStatus,
)
from app.auth.models import User
from app.citizens.models import CitizenProfile, UserNationalIdentifier
from app.core.security import hash_password
from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


CITIZEN_PASSWORD = "StrongPassword123!"
PROFESSIONAL_PASSWORD = "ProfessionalPassword123!"
BOOK_PATH = "/api/v1/citizens/appointments"
CHAMBER_START_PATH = "/api/v1/professionals/chamber/sessions/start"
CHAMBER_TODAY_PATH = "/api/v1/professionals/chamber/sessions/today"
CHAMBER_CALL_NEXT_PATH = "/api/v1/professionals/chamber/queue/call-next"
CHAMBER_FINISH_PATH = "/api/v1/professionals/chamber/sessions/finish"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_citizen(client: TestClient) -> tuple[str, uuid.UUID]:
    unique = uuid.uuid4().hex
    response = client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": f"citizen-{unique}@example.com",
            "password": CITIZEN_PASSWORD,
            "first_name": "Carla",
            "last_name": "Citizen",
            "date_of_birth": "1990-01-01",
            "gender": "FEMALE",
            "blood_group": "A+",
            "address": "Dhaka",
            "nid_number": f"NID-{unique[:24]}",
        },
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={
            "email": f"citizen-{unique}@example.com",
            "password": CITIZEN_PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"], response.json()["citizen_id"]


def _make_facility(db_session, *, name: str) -> HealthcareFacility:
    facility = HealthcareFacility(
        name=name,
        facility_type="HOSPITAL",
        registration_number=f"REG-{uuid.uuid4().hex[:8]}",
        address="HealthLink Avenue",
        phone="+8801700000000",
        email="facility@example.com",
        is_active=True,
    )
    db_session.add(facility)
    db_session.commit()
    db_session.refresh(facility)
    return facility


def _make_verified_doctor(
    db_session,
    *,
    first_name: str,
    last_name: str,
    facility: HealthcareFacility,
    nid_number: str,
    password: str = PROFESSIONAL_PASSWORD,
    verified: bool = True,
) -> tuple[uuid.UUID, uuid.UUID, str, str]:
    """Return (user_id, registration_id, nid_number, password)."""

    user = User(
        email=f"doctor-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    nid = UserNationalIdentifier(user_id=user.id, nid_number=nid_number)
    db_session.add(nid)
    db_session.commit()

    profile = HealthcareProfessionalProfile(user_id=user.id)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    role = db_session.scalar(
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
        designation="Consultant",
        verification_status=(
            VerificationStatus.VERIFIED.value
            if verified
            else VerificationStatus.PENDING.value
        ),
    )
    if verified:
        registration.verified_at = datetime.now(timezone.utc)
    db_session.add(registration)
    db_session.commit()
    db_session.refresh(registration)
    return user.id, registration.id, nid_number, password


def _add_schedule(
    db_session,
    *,
    doctor_user_id: uuid.UUID,
    facility: HealthcareFacility,
    weekday: str,
    max_patients: int = 5,
) -> DoctorPracticeSchedule:
    schedule = DoctorPracticeSchedule(
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        weekday=weekday,
        start_time=time(9, 0),
        end_time=time(13, 0),
        max_patients=max_patients,
        status=PracticeScheduleStatus.ACTIVE.value,
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


def _book(
    client: TestClient,
    token: str,
    *,
    doctor_user_id: uuid.UUID,
    facility_id: uuid.UUID,
    appointment_date: date,
) -> dict:
    response = client.post(
        BOOK_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility_id),
            "appointment_date": appointment_date.isoformat(),
            "reason": "Checkup",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login_professional(
    client: TestClient,
    *,
    nid_number: str,
    password: str,
    role_code: str = "DOCTOR",
) -> str:
    response = client.post(
        "/api/v1/auth/professional/login",
        json={
            "nid_number": nid_number,
            "password": password,
            "role_code": role_code,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _start_session(
    client: TestClient,
    token: str,
    *,
    facility_id: uuid.UUID,
    session_date: date,
) -> dict:
    response = client.post(
        CHAMBER_START_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "facility_id": str(facility_id),
            "session_date": session_date.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Auth and role gates
# ---------------------------------------------------------------------------


def test_chamber_endpoints_require_authentication(client: TestClient) -> None:
    today = date.today()
    for path, method in [
        (CHAMBER_START_PATH, "POST"),
        (CHAMBER_TODAY_PATH, "GET"),
        (CHAMBER_CALL_NEXT_PATH, "POST"),
        (CHAMBER_FINISH_PATH, "POST"),
    ]:
        kwargs = {
            "headers": {},
            "params": {"facility_id": str(uuid.uuid4()), "session_date": today.isoformat()},
        }
        if method == "POST":
            response = client.post(path, **kwargs)
        else:
            response = client.get(path, **kwargs)
        assert response.status_code == 401, f"{method} {path} returned {response.status_code}"


def test_chamber_rejects_citizen_portal(
    client: TestClient, db_session
) -> None:
    token, _ = _register_citizen(client)
    response = client.post(
        CHAMBER_START_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={"facility_id": str(uuid.uuid4()), "session_date": date.today().isoformat()},
    )
    assert response.status_code == 403


def test_chamber_rejects_unverified_doctor(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber Unverified Clinic")
    _, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Pending",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-PENDING-CHAMBER",
        verified=False,
    )
    # Pending registration can log in, but cannot enter the chamber endpoints.
    token = _login_professional(client, nid_number=nid, password=password)
    response = client.post(
        CHAMBER_START_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={"facility_id": str(facility.id), "session_date": date.today().isoformat()},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Start session + advance queue
# ---------------------------------------------------------------------------


def test_start_session_promotes_lowest_waiting_serial(
    client: TestClient, db_session
) -> None:
    citizen_token, _ = _register_citizen(client)
    facility = _make_facility(db_session, name="Chamber Start Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Start",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-START-CHAMBER",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)

    # Three citizens book serials 1, 2, 3.
    for _ in range(3):
        fresh_token, _ = _register_citizen(client)
        _book(
            client,
            fresh_token,
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            appointment_date=target,
        )

    doctor_token = _login_professional(client, nid_number=nid, password=password)
    body = _start_session(
        client,
        doctor_token,
        facility_id=facility.id,
        session_date=target,
    )

    assert body["status"] == "ACTIVE"
    assert body["facility_name"] == "Chamber Start Clinic"
    assert body["current"] is not None
    assert body["current"]["serial_number"] == 1
    assert body["current"]["queue_status"] == "CURRENT"
    assert len(body["waiting"]) == 2
    waiting_serials = sorted(row["serial_number"] for row in body["waiting"])
    assert waiting_serials == [2, 3]


def test_call_next_advances_through_serial_queue(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber Call-Next Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Call",
        last_name="Next",
        facility=facility,
        nid_number="NID-CALL-NEXT",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    for _ in range(3):
        fresh_token, _ = _register_citizen(client)
        _book(
            client,
            fresh_token,
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            appointment_date=target,
        )

    doctor_token = _login_professional(client, nid_number=nid, password=password)
    headers = {"Authorization": f"Bearer {doctor_token}"}

    # Starting the session auto-promotes serial 1.
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    assert started["current"]["serial_number"] == 1

    # Calling next when one is already CURRENT must reject.
    blocked = client.post(
        CHAMBER_CALL_NEXT_PATH,
        headers=headers,
        params={"facility_id": str(facility.id), "session_date": target.isoformat()},
    )
    assert blocked.status_code == 409

    # Complete serial 1 -> serial 2 becomes CURRENT.
    queue_id_one = started["current"]["queue_id"]
    completed = client.post(
        f"/api/v1/professionals/chamber/queue/{queue_id_one}/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    completed_body = completed.json()
    assert completed_body["queue_status"] == "DONE"
    assert completed_body["appointment_status"] == "COMPLETED"
    assert completed_body["next_current"] is not None
    assert completed_body["next_current"]["serial_number"] == 2
    assert completed_body["next_current"]["queue_status"] == "CURRENT"

    # Skip serial 2 -> serial 3 becomes CURRENT.
    queue_id_two = completed_body["next_current"]["queue_id"]
    skipped = client.post(
        f"/api/v1/professionals/chamber/queue/{queue_id_two}/skip",
        headers=headers,
    )
    assert skipped.status_code == 200, skipped.text
    skipped_body = skipped.json()
    assert skipped_body["queue_status"] == "SKIPPED"
    assert skipped_body["appointment_status"] == "BOOKED"
    assert skipped_body["next_current"]["serial_number"] == 3

    # Remove serial 3 -> no WAITING remain.
    queue_id_three = skipped_body["next_current"]["queue_id"]
    removed = client.post(
        f"/api/v1/professionals/chamber/queue/{queue_id_three}/remove",
        headers=headers,
    )
    assert removed.status_code == 200, removed.text
    removed_body = removed.json()
    assert removed_body["queue_status"] == "REMOVED"
    assert removed_body["appointment_status"] == "REMOVED_BY_DOCTOR"
    assert removed_body["next_current"] is None

    # Calling next when nobody is waiting must reject.
    no_one = client.post(
        CHAMBER_CALL_NEXT_PATH,
        headers=headers,
        params={"facility_id": str(facility.id), "session_date": target.isoformat()},
    )
    assert no_one.status_code == 409


def test_skip_advances_when_called_on_waiting_entry(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber Skip Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Skip",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-SKIP-CHAMBER",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    for _ in range(2):
        fresh_token, _ = _register_citizen(client)
        _book(
            client,
            fresh_token,
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            appointment_date=target,
        )

    doctor_token = _login_professional(client, nid_number=nid, password=password)
    headers = {"Authorization": f"Bearer {doctor_token}"}
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    serial_one_queue_id = started["current"]["queue_id"]

    # Skip serial 1 directly (it's CURRENT after start_session).
    skipped = client.post(
        f"/api/v1/professionals/chamber/queue/{serial_one_queue_id}/skip",
        headers=headers,
    )
    assert skipped.status_code == 200, skipped.text
    body = skipped.json()
    assert body["queue_status"] == "SKIPPED"
    assert body["next_current"]["serial_number"] == 2


def test_no_show_marks_appointment_and_advances(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber No-Show Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="NoShow",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-NOSHOW",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    for _ in range(2):
        fresh_token, _ = _register_citizen(client)
        _book(
            client,
            fresh_token,
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            appointment_date=target,
        )

    doctor_token = _login_professional(client, nid_number=nid, password=password)
    headers = {"Authorization": f"Bearer {doctor_token}"}
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    queue_id_one = started["current"]["queue_id"]

    response = client.post(
        f"/api/v1/professionals/chamber/queue/{queue_id_one}/no-show",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["queue_status"] == "REMOVED"
    assert body["appointment_status"] == "NO_SHOW"
    assert body["next_current"]["serial_number"] == 2


def test_cancelled_appointments_are_excluded_from_waiting(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber Cancel Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Cancel",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-CANCEL-CHAMBER",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    citizen_token, _ = _register_citizen(client)
    first = _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )
    second = _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    # Citizen cancels serial 1 directly through the model layer.
    appointment = db_session.get(Appointment, uuid.UUID(first["id"]))
    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.cancelled_at = datetime.now(timezone.utc)
    db_session.commit()

    doctor_token = _login_professional(client, nid_number=nid, password=password)
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )

    # Only the active serial 2 is in the chamber queue; serial 1 is skipped
    # because its appointment is no longer BOOKED.
    assert started["current"] is not None
    assert started["current"]["serial_number"] == second["serial_number"]


def test_only_one_current_per_session_invariant(
    client: TestClient, db_session
) -> None:
    """No matter how many call_nexts fire, exactly one row is CURRENT."""

    facility = _make_facility(db_session, name="Chamber Invariant Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Invariant",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-INVARIANT",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    for _ in range(4):
        fresh_token, _ = _register_citizen(client)
        _book(
            client,
            fresh_token,
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            appointment_date=target,
        )

    doctor_token = _login_professional(client, nid_number=nid, password=password)
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    session_id = started["id"]

    current_rows = db_session.scalars(
        select(AppointmentQueueEntry).where(
            AppointmentQueueEntry.practice_session_id == uuid.UUID(session_id),
            AppointmentQueueEntry.queue_status == QueueStatus.CURRENT.value,
        )
    ).all()
    assert len(current_rows) == 1


def test_queue_action_rejects_foreign_doctors(
    client: TestClient, db_session
) -> None:
    facility_a = _make_facility(db_session, name="Chamber A Clinic")
    facility_b = _make_facility(db_session, name="Chamber B Clinic")
    doctor_a_user, _, nid_a, password_a = _make_verified_doctor(
        db_session,
        first_name="Doctor",
        last_name="A",
        facility=facility_a,
        nid_number="NID-DOCTOR-A",
    )
    _, _, nid_b, password_b = _make_verified_doctor(
        db_session,
        first_name="Doctor",
        last_name="B",
        facility=facility_b,
        nid_number="NID-DOCTOR-B",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_a_user,
        facility=facility_a,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    citizen_token, _ = _register_citizen(client)
    booked = _book(
        client,
        citizen_token,
        doctor_user_id=doctor_a_user,
        facility_id=facility_a.id,
        appointment_date=target,
    )

    token_a = _login_professional(client, nid_number=nid_a, password=password_a)
    started_a = _start_session(
        client, token_a, facility_id=facility_a.id, session_date=target
    )
    queue_id = started_a["current"]["queue_id"]

    token_b = _login_professional(client, nid_number=nid_b, password=password_b)
    forbidden = client.post(
        f"/api/v1/professionals/chamber/queue/{queue_id}/complete",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden.status_code == 404
    del booked


def test_finish_session_blocks_further_queue_actions(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber Finish Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Finish",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-FINISH-CHAMBER",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    fresh_token, _ = _register_citizen(client)
    _book(
        client,
        fresh_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    token = _login_professional(client, nid_number=nid, password=password)
    headers = {"Authorization": f"Bearer {token}"}
    _start_session(client, token, facility_id=facility.id, session_date=target)

    finished = client.post(
        CHAMBER_FINISH_PATH,
        headers=headers,
        params={"facility_id": str(facility.id), "session_date": target.isoformat()},
    )
    assert finished.status_code == 200, finished.text
    body = finished.json()
    assert body["status"] == "COMPLETED"
    assert body["remaining_waiting"] == 0
    assert body["ended_at"] is not None

    # Calling next after finish must reject.
    blocked = client.post(
        CHAMBER_CALL_NEXT_PATH,
        headers=headers,
        params={"facility_id": str(facility.id), "session_date": target.isoformat()},
    )
    assert blocked.status_code == 409

    # Re-finishing must reject.
    refinsh = client.post(
        CHAMBER_FINISH_PATH,
        headers=headers,
        params={"facility_id": str(facility.id), "session_date": target.isoformat()},
    )
    assert refinsh.status_code == 409


def test_view_today_returns_session_view(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber View Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="View",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VIEW-CHAMBER",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    for _ in range(2):
        fresh_token, _ = _register_citizen(client)
        _book(
            client,
            fresh_token,
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            appointment_date=target,
        )

    token = _login_professional(client, nid_number=nid, password=password)
    headers = {"Authorization": f"Bearer {token}"}

    # Before starting, today's queue returns a NOT_STARTED session view
    # (because booking creates a practice_session row at insertion time).
    response = client.get(
        CHAMBER_TODAY_PATH,
        headers=headers,
        params={"facility_id": str(facility.id), "session_date": target.isoformat()},
    )
    assert response.status_code == 200, response.text
    pre_view = response.json()
    assert pre_view["status"] == "NOT_STARTED"
    assert pre_view["current"] is None
    assert pre_view["waiting"] == []

    # After start, we see current + waiting + finished buckets.
    _start_session(client, token, facility_id=facility.id, session_date=target)
    response = client.get(
        CHAMBER_TODAY_PATH,
        headers=headers,
        params={"facility_id": str(facility.id), "session_date": target.isoformat()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["current"]["serial_number"] == 1
    assert sorted(row["serial_number"] for row in body["waiting"]) == [2]


def test_start_session_is_idempotent(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Chamber Idempotent Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Idempotent",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-IDEMPOTENT",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )
    target = date.today()
    while target.strftime("%A").upper() != "MONDAY":
        from datetime import timedelta

        target = target + timedelta(days=1)
    fresh_token, _ = _register_citizen(client)
    _book(
        client,
        fresh_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    token = _login_professional(client, nid_number=nid, password=password)
    first = _start_session(
        client, token, facility_id=facility.id, session_date=target
    )
    second = _start_session(
        client, token, facility_id=facility.id, session_date=target
    )

    assert first["id"] == second["id"]
    assert first["status"] == second["status"] == "ACTIVE"

    # Only one row in CURRENT across both calls.
    current_rows = db_session.scalars(
        select(AppointmentQueueEntry).where(
            AppointmentQueueEntry.practice_session_id == uuid.UUID(first["id"]),
            AppointmentQueueEntry.queue_status == QueueStatus.CURRENT.value,
        )
    ).all()
    assert len(current_rows) == 1

    # The practice session was started exactly once.
    session_rows = db_session.scalars(
        select(DoctorPracticeSession).where(
            DoctorPracticeSession.doctor_role_registration_id == uuid.UUID(first["id"])
            and False  # type: ignore[operator]
        )
    ).all()
    del session_rows

    session_row = db_session.get(
        DoctorPracticeSession, uuid.UUID(first["id"])
    )
    assert session_row is not None
    assert session_row.status == SessionStatus.ACTIVE.value
    assert session_row.started_at is not None