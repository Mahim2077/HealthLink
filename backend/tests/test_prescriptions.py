from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest
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
from app.prescriptions.models import (
    Prescription,
    PrescriptionDocument,
    PrescriptionItem,
)
from app.prescriptions.storage import (
    LocalPrescriptionStorage,
    PrescriptionStorage,
    reset_prescription_storage_for_tests,
)
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)
from app.visits.models import MedicalVisit, VisitStatus


CITIZEN_PASSWORD = "StrongPassword123!"
PROFESSIONAL_PASSWORD = "ProfessionalPassword123!"
BOOK_PATH = "/api/v1/citizens/appointments"
CHAMBER_START_PATH = "/api/v1/professionals/chamber/sessions/start"
DOCTOR_START_FOR_CURRENT = "/api/v1/doctors/me/visits/start-for-current/{queue_id}"
CREATE_PRESCRIPTION_PATH = "/api/v1/visits/{visit_id}/prescription"
DOCTOR_PRESCRIPTION_PATH = "/api/v1/prescriptions/{prescription_id}"
CITIZEN_PRESCRIPTION_PATH = "/api/v1/prescriptions/{prescription_id}"
PDF_PATH = "/api/v1/prescriptions/{prescription_id}/pdf"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_citizen(client: TestClient) -> tuple[str, uuid.UUID]:
    unique = uuid.uuid4().hex
    response = client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": f"citizen-rx-{unique}@example.com",
            "password": CITIZEN_PASSWORD,
            "first_name": "Rita",
            "last_name": "Patient",
            "date_of_birth": "1985-05-05",
            "gender": "FEMALE",
            "blood_group": "O+",
            "address": "Dhaka",
            "nid_number": f"NID-RX-{unique[:20]}",
        },
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={
            "email": f"citizen-rx-{unique}@example.com",
            "password": CITIZEN_PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"], response.json()["citizen_id"]


def _make_facility(db_session, *, name: str) -> HealthcareFacility:
    facility = HealthcareFacility(
        name=name,
        facility_type="HOSPITAL",
        registration_number=f"REG-RX-{uuid.uuid4().hex[:8]}",
        address="HealthLink Avenue",
        phone="+8801700000000",
        email="rx-facility@example.com",
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
    bmdc: str | None = None,
    password: str = PROFESSIONAL_PASSWORD,
    verified: bool = True,
) -> tuple[uuid.UUID, uuid.UUID, str, str]:
    """Return (user_id, registration_id, nid_number, password)."""

    user = User(
        email=f"doctor-rx-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password(password),
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

    if bmdc is not None:
        detail = DoctorRegistrationDetail(
            professional_role_registration_id=registration.id,
            bmdc_registration_number=bmdc,
        )
        db_session.add(detail)
        db_session.commit()
        db_session.refresh(detail)

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
            today = today + timedelta(days=7 - delta)
            break
    return today


def _set_up_visit(
    client: TestClient,
    db_session,
    *,
    clinic_name: str,
    weekday: str,
    doctor_first_name: str = "Heal",
    doctor_last_name: str = "Rx",
    nid_number: str = "NID-RX-DEFAULT",
    bmdc: str = "BMDC-RX-001",
) -> tuple[str, uuid.UUID, uuid.UUID]:
    """Book, start session, open visit.

    Returns (doctor_token, visit_id, registration_id).
    """

    facility = _make_facility(db_session, name=clinic_name)
    doctor_user_id, registration_id, nid, password = _make_verified_doctor(
        db_session,
        first_name=doctor_first_name,
        last_name=doctor_last_name,
        facility=facility,
        nid_number=nid_number,
        bmdc=bmdc,
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday=weekday,
    )
    target = _next_matching_date(weekday)

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    doctor_token = _login_professional(client, nid_number=nid, password=password)
    started = _start_session(
        client,
        doctor_token,
        facility_id=facility.id,
        session_date=target,
    )
    queue_id = started["current"]["queue_id"]
    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert opened.status_code == 200, opened.text
    return doctor_token, uuid.UUID(opened.json()["id"]), registration_id


def _login_citizen_for_visit(
    client: TestClient, db_session, visit_id: uuid.UUID
) -> str:
    visit = db_session.get(MedicalVisit, visit_id)
    assert visit is not None
    profile = db_session.get(CitizenProfile, visit.citizen_id)
    assert profile is not None
    user = db_session.get(User, profile.user_id)
    assert user is not None
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": user.email, "password": CITIZEN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


_VALID_PAYLOAD = {
    "items": [
        {
            "medicine_name": "Paracetamol",
            "dosage": "500 mg",
            "frequency": "1+0+1",
            "duration": "5 days",
            "instructions": "After meals",
        },
        {
            "medicine_name": "Amoxicillin",
            "dosage": "500 mg",
            "frequency": "1+1+1",
            "duration": "7 days",
            "instructions": None,
        },
    ],
    "diagnostic_information": "Acute pharyngitis",
    "medical_advice": "Warm gargles, plenty of fluids",
    "notes": "Follow-up if no improvement in 3 days",
}


# ---------------------------------------------------------------------------
# Storage fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def prescription_storage(tmp_path, monkeypatch):
    """Provide a fresh local prescription storage backed by ``tmp_path``.

    The default ``<backend>/.prescription_storage`` directory is replaced
    with a per-test directory so generated PDFs do not pollute the
    repository and so failures are inspectable per test.
    """

    storage = LocalPrescriptionStorage(tmp_path)
    reset_prescription_storage_for_tests(storage)
    yield storage
    reset_prescription_storage_for_tests(None)


# ---------------------------------------------------------------------------
# Authorisation / role gates
# ---------------------------------------------------------------------------


def _paths_for_visit(visit_id: uuid.UUID) -> list[tuple[str, str]]:
    return [
        (CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id), "POST"),
        (DOCTOR_PRESCRIPTION_PATH.format(prescription_id=uuid.uuid4()), "GET"),
        (DOCTOR_PRESCRIPTION_PATH.format(prescription_id=uuid.uuid4()), "PUT"),
        (CITIZEN_PRESCRIPTION_PATH.format(prescription_id=uuid.uuid4()), "GET"),
        (PDF_PATH.format(prescription_id=uuid.uuid4()), "GET"),
    ]


def test_prescription_endpoints_require_authentication(
    client: TestClient, db_session
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Auth Gate Clinic", weekday="MONDAY"
    )
    # Even after creating resources, unauthenticated callers must bounce.
    response = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id), json=_VALID_PAYLOAD
    )
    assert response.status_code == 401, response.text
    response = client.get(
        DOCTOR_PRESCRIPTION_PATH.format(prescription_id=uuid.uuid4())
    )
    assert response.status_code == 401, response.text


def test_create_prescription_requires_verified_doctor(
    client: TestClient, db_session
) -> None:
    doctor_token, visit_id, registration_id = _set_up_visit(
        client,
        db_session,
        clinic_name="Rx Pending Doctor Clinic",
        weekday="MONDAY",
        nid_number="NID-RX-PENDING",
        bmdc="BMDC-PENDING",
    )
    registration = db_session.get(
        ProfessionalRoleRegistration, registration_id
    )
    assert registration is not None
    registration.verification_status = VerificationStatus.PENDING.value
    registration.verified_at = None
    db_session.commit()

    response = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert response.status_code == 403, response.text


def test_create_prescription_writes_payload_and_pdf(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Create Clinic", weekday="MONDAY",
        nid_number="NID-RX-CREATE", bmdc="BMDC-CREATE",
    )
    response = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status" if "status" in body else "items"]
    assert len(body["items"]) == 2
    assert body["pdf_available"] is True
    assert body["pdf_file_name"] == "prescription.pdf"
    prescription_id = uuid.UUID(body["id"])

    persisted = db_session.get(Prescription, prescription_id)
    assert persisted is not None
    assert persisted.visit_id == visit_id
    assert persisted.diagnostic_information == _VALID_PAYLOAD[
        "diagnostic_information"
    ]
    assert persisted.notes == _VALID_PAYLOAD["notes"]
    assert len(persisted.items) == 2

    document = db_session.scalar(
        select(PrescriptionDocument).where(
            PrescriptionDocument.prescription_id == prescription_id
        )
    )
    assert document is not None
    assert document.content_type == "application/pdf"
    assert prescription_storage.exists(document.storage_key)


def test_create_prescription_rejects_second_per_visit(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Duplicate Clinic", weekday="MONDAY",
        nid_number="NID-RX-DUP", bmdc="BMDC-DUP",
    )
    first = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert second.status_code == 409, second.text


def test_doctor_can_read_own_prescription(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Read Clinic", weekday="MONDAY",
        nid_number="NID-RX-READ", bmdc="BMDC-READ",
    )
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert created.status_code == 201, created.text
    prescription_id = created.json()["id"]

    response = client.get(
        DOCTOR_PRESCRIPTION_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == prescription_id
    assert body["pdf_available"] is True


def test_update_prescription_replaces_items_and_regenerates_pdf(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Edit Clinic", weekday="MONDAY",
        nid_number="NID-RX-EDIT", bmdc="BMDC-EDIT",
    )
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    prescription_id = created.json()["id"]
    original_doc = db_session.scalar(
        select(PrescriptionDocument).where(
            PrescriptionDocument.prescription_id == uuid.UUID(prescription_id)
        )
    )
    assert original_doc is not None

    new_payload = {
        "items": [
            {
                "medicine_name": "Ibuprofen",
                "dosage": "400 mg",
                "frequency": "1+0+1",
                "duration": "3 days",
                "instructions": "After meals, avoid on empty stomach",
            }
        ],
        "diagnostic_information": "Tension headache",
        "medical_advice": "Reduce screen time",
        "notes": None,
    }
    response = client.put(
        DOCTOR_PRESCRIPTION_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=new_payload,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["medicine_name"] == "Ibuprofen"
    assert body["diagnostic_information"] == "Tension headache"
    assert body["notes"] is None

    refreshed_doc = db_session.scalar(
        select(PrescriptionDocument).where(
            PrescriptionDocument.prescription_id == uuid.UUID(prescription_id)
        )
    )
    assert refreshed_doc is not None
    assert refreshed_doc.id == original_doc.id
    assert refreshed_doc.storage_key == original_doc.storage_key
    assert refreshed_doc.file_size_bytes > 0


def test_foreign_doctor_cannot_read_or_edit_prescription(
    client: TestClient, db_session, prescription_storage
) -> None:
    facility = _make_facility(db_session, name="Rx Foreign Doctor Clinic")

    alice_user_id, _, nid_a, password_a = _make_verified_doctor(
        db_session,
        first_name="Alice",
        last_name="Rx",
        facility=facility,
        nid_number="NID-RX-FA",
        bmdc="BMDC-FA",
    )
    _add_schedule(
        db_session,
        doctor_user_id=alice_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=alice_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )

    alice_token = _login_professional(
        client, nid_number=nid_a, password=password_a
    )
    started = _start_session(
        client, alice_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]
    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    visit_id = uuid.UUID(opened.json()["id"])
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {alice_token}"},
        json=_VALID_PAYLOAD,
    )
    assert created.status_code == 201, created.text
    prescription_id = created.json()["id"]

    # Register Bob, a different verified doctor at the same facility.
    _, _, nid_b, password_b = _make_verified_doctor(
        db_session,
        first_name="Bob",
        last_name="Rx",
        facility=facility,
        nid_number="NID-RX-FB",
        bmdc="BMDC-FB",
    )
    bob_token = _login_professional(
        client, nid_number=nid_b, password=password_b
    )

    forbidden_read = client.get(
        DOCTOR_PRESCRIPTION_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert forbidden_read.status_code == 403, forbidden_read.text

    forbidden_edit = client.put(
        DOCTOR_PRESCRIPTION_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {bob_token}"},
        json=_VALID_PAYLOAD,
    )
    assert forbidden_edit.status_code == 403, forbidden_edit.text


def test_create_prescription_rejects_forbidden_identifier_in_payload(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Forbidden Clinic", weekday="MONDAY",
        nid_number="NID-RX-FORB", bmdc="BMDC-FORB",
    )
    bad_payload = {
        "items": [
            {
                "medicine_name": "Paracetamol",
                "dosage": "500 mg",
                "frequency": "1+0+1",
                "duration": "5 days",
                "instructions": "Patient NID-12345-678",
            }
        ],
        "diagnostic_information": "Checkup",
        "medical_advice": "Rest",
        "notes": None,
    }
    response = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=bad_payload,
    )
    assert response.status_code == 400, response.text


def test_citizen_can_read_own_prescription(
    client: TestClient, db_session, prescription_storage
) -> None:
    # Phase 13 rule: a citizen reads a prescription via citizen_id == own.
    # We register the citizen AFTER the doctor opens the visit so that
    # we know exactly whose prescription this is. The first citizen
    # registered by _set_up_visit is the visit's citizen. Use that fact
    # by directly querying the visit row to recover the citizen_id and
    # then re-registering a second citizen (the "other" citizen) to
    # assert the positive path via login.
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Citizen Read Clinic", weekday="MONDAY",
        nid_number="NID-RX-CREAD", bmdc="BMDC-CREAD",
    )
    visit_row = db_session.get(MedicalVisit, visit_id)
    assert visit_row is not None
    citizen_id = visit_row.citizen_id

    # Author a prescription as the verified doctor.
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert created.status_code == 201, created.text
    prescription_id = created.json()["id"]

    # ``MedicalVisit.citizen_id`` references ``CitizenProfile.id``, not
    # ``User.id``. Resolve the owning user before logging the citizen in.
    citizen_profile = db_session.get(CitizenProfile, citizen_id)
    assert citizen_profile is not None
    citizen_user = db_session.get(User, citizen_profile.user_id)
    assert citizen_user is not None
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={
            "email": citizen_user.email,
            "password": CITIZEN_PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    citizen_token = login.json()["access_token"]

    response = client.get(
        CITIZEN_PRESCRIPTION_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == prescription_id
    assert body["citizen_id"] == str(citizen_id)


def test_citizen_cannot_edit_own_prescription(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client,
        db_session,
        clinic_name="Rx Citizen Edit Denied Clinic",
        weekday="MONDAY",
        nid_number="NID-RX-CEDIT",
        bmdc="BMDC-CEDIT",
    )
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert created.status_code == 201, created.text

    citizen_token = _login_citizen_for_visit(client, db_session, visit_id)
    response = client.put(
        CITIZEN_PRESCRIPTION_PATH.format(
            prescription_id=created.json()["id"]
        ),
        headers={"Authorization": f"Bearer {citizen_token}"},
        json=_VALID_PAYLOAD,
    )
    assert response.status_code == 403, response.text


def test_citizen_cannot_read_another_citizens_prescription(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx Citizen Denied Clinic", weekday="MONDAY",
        nid_number="NID-RX-CD", bmdc="BMDC-CD",
    )
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    prescription_id = created.json()["id"]

    other_token, _ = _register_citizen(client)
    response = client.get(
        CITIZEN_PRESCRIPTION_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404, response.text


def test_pdf_stream_returns_application_pdf(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx PDF Stream Clinic", weekday="MONDAY",
        nid_number="NID-RX-PDF", bmdc="BMDC-PDF",
    )
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    prescription_id = created.json()["id"]

    response = client.get(
        PDF_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    body = response.content
    assert body.startswith(b"%PDF")
    assert b"NID" not in body
    assert b"BCN" not in body
    assert b"birth certificate" not in body.lower()


def test_pdf_stream_rejects_non_author_doctor(
    client: TestClient, db_session, prescription_storage
) -> None:
    facility = _make_facility(db_session, name="Rx PDF Foreign Clinic")
    alice_user_id, _, nid_a, password_a = _make_verified_doctor(
        db_session,
        first_name="PdfAlice",
        last_name="Rx",
        facility=facility,
        nid_number="NID-RX-PA",
        bmdc="BMDC-PA",
    )
    _add_schedule(
        db_session,
        doctor_user_id=alice_user_id,
        facility=facility,
        weekday="MONDAY",
    )
    target = _next_matching_date("MONDAY")

    citizen_token, _ = _register_citizen(client)
    _book(
        client,
        citizen_token,
        doctor_user_id=alice_user_id,
        facility_id=facility.id,
        appointment_date=target,
    )
    alice_token = _login_professional(
        client, nid_number=nid_a, password=password_a
    )
    started = _start_session(
        client, alice_token, facility_id=facility.id, session_date=target
    )
    queue_id = started["current"]["queue_id"]
    opened = client.post(
        DOCTOR_START_FOR_CURRENT.format(queue_id=queue_id),
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    visit_id = uuid.UUID(opened.json()["id"])
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {alice_token}"},
        json=_VALID_PAYLOAD,
    )
    prescription_id = created.json()["id"]

    _, _, nid_b, password_b = _make_verified_doctor(
        db_session,
        first_name="PdfBob",
        last_name="Rx",
        facility=facility,
        nid_number="NID-RX-PB",
        bmdc="BMDC-PB",
    )
    bob_token = _login_professional(
        client, nid_number=nid_b, password=password_b
    )
    response = client.get(
        PDF_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403, response.text


def test_pdf_stream_allows_owning_citizen(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client, db_session, clinic_name="Rx PDF Citizen Block Clinic", weekday="MONDAY",
        nid_number="NID-RX-PCB", bmdc="BMDC-PCB",
    )
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    prescription_id = created.json()["id"]

    visit_row = db_session.get(MedicalVisit, visit_id)
    assert visit_row is not None
    citizen_profile = db_session.get(CitizenProfile, visit_row.citizen_id)
    assert citizen_profile is not None
    citizen_user = db_session.get(User, citizen_profile.user_id)
    assert citizen_user is not None
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={
            "email": citizen_user.email,
            "password": CITIZEN_PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    citizen_token = login.json()["access_token"]
    response = client.get(
        PDF_PATH.format(prescription_id=prescription_id),
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")


class _FailingPrescriptionStorage(PrescriptionStorage):
    def save(self, prescription_id, file_name: str, payload: bytes) -> str:
        raise OSError("simulated object storage outage")

    def load(self, storage_key: str) -> bytes:
        raise FileNotFoundError(storage_key)

    def delete(self, storage_key: str) -> None:
        return None

    def exists(self, storage_key: str) -> bool:
        return False


def test_pdf_failure_preserves_structured_record_and_put_retries_generation(
    client: TestClient, db_session, prescription_storage
) -> None:
    doctor_token, visit_id, _ = _set_up_visit(
        client,
        db_session,
        clinic_name="Rx Durable Retry Clinic",
        weekday="MONDAY",
        nid_number="NID-RX-RETRY",
        bmdc="BMDC-RETRY",
    )
    reset_prescription_storage_for_tests(_FailingPrescriptionStorage())
    created = client.post(
        CREATE_PRESCRIPTION_PATH.format(visit_id=visit_id),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert created.status_code == 201, created.text
    assert created.json()["pdf_available"] is False

    prescription_id = uuid.UUID(created.json()["id"])
    persisted = db_session.get(Prescription, prescription_id)
    assert persisted is not None
    assert len(persisted.items) == 2
    assert db_session.scalar(
        select(PrescriptionDocument).where(
            PrescriptionDocument.prescription_id == prescription_id
        )
    ) is None

    reset_prescription_storage_for_tests(prescription_storage)
    retried = client.put(
        DOCTOR_PRESCRIPTION_PATH.format(
            prescription_id=prescription_id
        ),
        headers={"Authorization": f"Bearer {doctor_token}"},
        json=_VALID_PAYLOAD,
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()["pdf_available"] is True
