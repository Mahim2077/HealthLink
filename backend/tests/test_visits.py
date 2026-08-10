from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

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
from app.visits.models import MedicalVisit, VisitStatus


CITIZEN_PASSWORD = "StrongPassword123!"
PROFESSIONAL_PASSWORD = "ProfessionalPassword123!"
BOOK_PATH = "/api/v1/citizens/appointments"
CHAMBER_START_PATH = "/api/v1/professionals/chamber/sessions/start"

DOCTOR_CURRENT_PATH = "/api/v1/doctors/me/visits/current-patient"
DOCTOR_START_FOR_CURRENT = "/api/v1/doctors/me/visits/start-for-current/{queue_id}"
DOCTOR_VISIT_PATH = "/api/v1/doctors/me/visits/{visit_id}"

CITIZEN_VISITS_TODAY = "/api/v1/citizens/me/visits/today"
CITIZEN_VISIT_PATH = "/api/v1/citizens/me/visits/{visit_id}"


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
            "first_name": "Vera",
            "last_name": "Visitor",
            "date_of_birth": "1985-05-05",
            "gender": "FEMALE",
            "blood_group": "O+",
            "address": "Dhaka",
            "nid_number": f"NID-V-{unique[:24]}",
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
        email="visits-facility@example.com",
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
    verified: bool = True,
) -> tuple[uuid.UUID, uuid.UUID, str, str]:
    user = User(
        email=f"doctor-visits-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password(PROFESSIONAL_PASSWORD),
        first_name=first_name,
        last_name=last_name,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    db_session.add(UserNationalIdentifier(user_id=user.id, nid_number=nid_number))
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
    return user.id, registration.id, nid_number, PROFESSIONAL_PASSWORD


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
            "reason": "Consultation",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


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


def _next_matching_date(target_weekday: str) -> date:
    today = date.today()
    delta = 0
    while today.strftime("%A").upper() != target_weekday:
        today = today + timedelta(days=1)
        delta += 1
        if delta > 7:
            # Use the weekday in the next calendar week to keep tests fast.
            today = today + timedelta(days=7 - delta)
            break
    return today


# ---------------------------------------------------------------------------
# Auth + role gates
# ---------------------------------------------------------------------------


def test_visits_endpoints_require_authentication(client: TestClient) -> None:
    for path, method in [
        (DOCTOR_CURRENT_PATH, "GET"),
        (DOCTOR_VISIT_PATH.format(visit_id=uuid.uuid4()), "GET"),
        (CITIZEN_VISITS_TODAY, "GET"),
        (CITIZEN_VISIT_PATH.format(visit_id=uuid.uuid4()), "GET"),
    ]:
        if method == "GET":
            response = client.get(path)
        else:
            response = client.post(path)
        assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


def test_doctor_visits_reject_citizen_portal(
    client: TestClient, db_session
) -> None:
    token, _ = _register_citizen(client)
    response = client.get(
        DOCTOR_CURRENT_PATH,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_citizen_visits_reject_doctor_portal(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Citizen-Reject Clinic")
    _, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Reject",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-REJECT",
    )
    token = _login_professional(client, nid_number=nid, password=password)
    response = client.get(
        CITIZEN_VISITS_TODAY,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_doctor_visits_reject_unverified_doctor(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Unverified Clinic")
    _, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Pending",
        last_name="Visits",
        facility=facility,
        nid_number="NID-VISITS-PENDING",
        verified=False,
    )
    token = _login_professional(client, nid_number=nid, password=password)
    response = client.get(
        DOCTOR_CURRENT_PATH,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Doctor workspace happy path
# ---------------------------------------------------------------------------


def test_current_patient_returns_null_without_active_session(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Empty Clinic")
    _, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Empty",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-EMPTY",
    )
    token = _login_professional(client, nid_number=nid, password=password)
    response = client.get(
        DOCTOR_CURRENT_PATH,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json() is None


def test_current_patient_returns_joint_view_with_active_session(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Active Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Active",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-ACTIVE",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=5,
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(
        client, nid_number=nid, password=password
    )
    started = _start_session(
        client,
        doctor_token,
        facility_id=facility.id,
        session_date=target,
    )
    assert started["current"]["serial_number"] == 1

    response = client.get(
        DOCTOR_CURRENT_PATH,
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body is not None
    assert body["serial_number"] == 1
    assert body["facility_name"] == "Visits Active Clinic"
    assert body["patient"]["full_name"].startswith("Vera")


def test_start_for_current_creates_draft_and_is_idempotent(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Start Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Start",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-START",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=5,
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(
        client, nid_number=nid, password=password
    )
    started = _start_session(
        client,
        doctor_token,
        facility_id=facility.id,
        session_date=target,
    )
    queue_id = started["current"]["queue_id"]

    # First call creates the draft visit.
    response = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["status"] == "DRAFT"
    visit_id = first["id"]

    # Second call returns the same visit.
    second_response = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert second_response.status_code == 200, second_response.text
    second = second_response.json()
    assert second["id"] == visit_id

    persisted = db_session.scalar(
        select(MedicalVisit).where(MedicalVisit.id == uuid.UUID(visit_id))
    )
    assert persisted is not None
    assert persisted.status == VisitStatus.DRAFT.value


def test_start_for_current_rejects_foreign_queue_entry(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Foreign Queue Clinic")

    doctor_a_user_id, _, nid_a, password_a = _make_verified_doctor(
        db_session,
        first_name="Alice",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-FA",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_a_user_id,
        facility=facility,
        weekday="MONDAY",
    )

    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_a_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_a_token = _login_professional(
        client, nid_number=nid_a, password=password_a
    )
    started = _start_session(
        client,
        doctor_a_token,
        facility_id=facility.id,
        session_date=target,
    )
    foreign_queue_id = started["current"]["queue_id"]

    # Second verified doctor (Bob) tries to open Alice's current queue row.
    _, _, nid_b, password_b = _make_verified_doctor(
        db_session,
        first_name="Bob",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-FB",
    )
    doctor_b_token = _login_professional(
        client, nid_number=nid_b, password=password_b
    )
    response = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=foreign_queue_id),
        headers={"Authorization": f"Bearer {doctor_b_token}"},
    )
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# Doctor draft update lifecycle
# ---------------------------------------------------------------------------


def test_update_visit_persists_draft_and_then_blocks_when_finalized(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Edit Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Edit",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-EDIT",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(
        client, nid_number=nid, password=password
    )
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]

    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    visit_id = opened.json()["id"]

    updated = client.put(
        DOCTOR_VISIT_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json={
            "chief_complaint": "Sore throat",
            "clinical_notes": "Throat appears inflamed",
            "diagnosis": "Acute pharyngitis",
            "follow_up_instructions": "Return in 3 days if not better",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["chief_complaint"] == "Sore throat"
    assert body["diagnosis"] == "Acute pharyngitis"
    assert body["status"] == "DRAFT"

    # Mark the visit finalized directly and try to edit again -> 409.
    visit_row = db_session.get(MedicalVisit, uuid.UUID(visit_id))
    assert visit_row is not None
    visit_row.status = VisitStatus.FINALIZED.value
    visit_row.finalized_at = datetime.now(timezone.utc)
    db_session.commit()

    follow_up = client.put(
        DOCTOR_VISIT_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json={"chief_complaint": "Sore throat, worse"},
    )
    assert follow_up.status_code == 409, follow_up.text


def test_foreign_doctor_cannot_update_someone_elses_visit(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Foreign Edit Clinic")

    doctor_a_user_id, _, nid_a, password_a = _make_verified_doctor(
        db_session,
        first_name="Alice",
        last_name="EditDoctor",
        facility=facility,
        nid_number="NID-VISITS-EA",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_a_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_a_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_a_token = _login_professional(
        client, nid_number=nid_a, password=password_a
    )
    started = _start_session(
        client, doctor_a_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]

    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_a_token}"},
    )
    visit_id = opened.json()["id"]

    _, _, nid_b, password_b = _make_verified_doctor(
        db_session,
        first_name="Bob",
        last_name="EditDoctor",
        facility=facility,
        nid_number="NID-VISITS-EB",
    )
    doctor_b_token = _login_professional(
        client, nid_number=nid_b, password=password_b
    )
    # Bob cannot reach Alice's visit at all because he has no current patient.
    response = client.put(
        DOCTOR_VISIT_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_b_token}"},
        json={"chief_complaint": "Trespass"},
    )
    assert response.status_code == 404, response.text


def test_doctor_can_read_own_visit(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Read Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Read",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-READ",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(
        client, nid_number=nid, password=password
    )
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]
    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    visit_id = opened.json()["id"]

    response = client.get(
        DOCTOR_VISIT_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == visit_id


# ---------------------------------------------------------------------------
# Citizen read path
# ---------------------------------------------------------------------------


def test_citizen_sees_own_visits_today(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Citizen Today Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Today",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-TODAY",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(
        client, nid_number=nid, password=password
    )
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]
    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    visit_id = opened.json()["id"]

    citizen_response = client.get(
        CITIZEN_VISITS_TODAY,
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert citizen_response.status_code == 200, citizen_response.text
    payload = citizen_response.json()
    assert len(payload["visits"]) == 1
    summary = payload["visits"][0]
    assert summary["id"] == visit_id
    assert summary["facility_name"] == "Visits Citizen Today Clinic"
    assert summary["status"] == "DRAFT"


def test_citizen_cannot_read_another_citizens_visit(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Citizen Foreign Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Cross",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-CROSS",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    # Citizen A books and gets a visit.
    citizen_a_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_a_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(
        client, nid_number=nid, password=password
    )
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]
    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    visit_id = opened.json()["id"]

    # Citizen B should not see Citizen A's visit.
    citizen_b_token, _ = _register_citizen(client)
    response = client.get(
        CITIZEN_VISIT_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {citizen_b_token}"},
    )
    assert response.status_code == 404, response.text


def test_citizen_can_read_own_visit_detail(
    client: TestClient, db_session
) -> None:
    facility = _make_facility(db_session, name="Visits Citizen Detail Clinic")
    doctor_user_id, _, nid, password = _make_verified_doctor(
        db_session,
        first_name="Detail",
        last_name="Doctor",
        facility=facility,
        nid_number="NID-VISITS-DETAIL",
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(
        client, nid_number=nid, password=password
    )
    started = _start_session(
        client, doctor_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]
    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    visit_id = opened.json()["id"]

    response = client.get(
        CITIZEN_VISIT_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == visit_id
    assert body["access_source"] == "citizen"
    assert body["patient"]["full_name"].startswith("Vera")
