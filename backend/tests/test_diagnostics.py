from __future__ import annotations

import uuid
import pytest
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.appointments.models import Appointment, AppointmentQueueEntry, AppointmentStatus, DoctorPracticeSession, QueueStatus, SessionStatus
from app.auth.constants import Portal
from app.auth.models import User
from app.auth.service import AuthService
from app.citizens.models import CitizenProfile
from app.core.config import Settings
from app.diagnostics.models import DiagnosticTest
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import HealthcareProfessionalProfile, ProfessionalRole, ProfessionalRoleRegistration
from app.visits.models import MedicalVisit, VisitStatus
from app.visits.repository import VisitsRepository
from app.visits.dependencies import CurrentPatientAccess
from app.diagnostics.service import DiagnosticsService
from app.diagnostics.schemas import DiagnosticTestCreateRequest
from app.core.exceptions import HealthLinkError


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user(db, name: str) -> User:
    user = User(email=f"{name}-{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", first_name=name, last_name="Tester")
    db.add(user); db.commit(); db.refresh(user)
    return user


def _facility(db, name: str = "Diagnostics Centre") -> HealthcareFacility:
    item = HealthcareFacility(name=name, facility_type="HOSPITAL", address="Dhaka", is_active=True)
    db.add(item); db.commit(); db.refresh(item)
    return item


def _registration(db, facility, role_code: ProfessionalRoleCode, *, verified: bool = True):
    user = _user(db, role_code.value)
    profile = HealthcareProfessionalProfile(user_id=user.id); db.add(profile); db.flush()
    role = db.scalar(select(ProfessionalRole).where(ProfessionalRole.code == role_code.value)); assert role
    registration = ProfessionalRoleRegistration(professional_id=profile.id, role_id=role.id, facility_id=facility.id, facility_name_submitted=facility.name, designation="Senior", verification_status=VerificationStatus.VERIFIED.value if verified else VerificationStatus.PENDING.value, verified_at=datetime.now(UTC) if verified else None)
    db.add(registration); db.commit(); db.refresh(registration)
    return user, registration


def _citizen(db, name: str):
    user = _user(db, name)
    profile = CitizenProfile(user_id=user.id, date_of_birth=date(1990, 1, 1), gender="OTHER")
    db.add(profile); db.commit(); db.refresh(profile)
    return user, profile


def _token(db, settings, user, portal, registration=None):
    return AuthService(db, settings).create_session(user.id, portal, active_professional_role_registration_id=registration.id if registration else None).access_token


def _queue(db, doctor_registration, facility, citizen, *, current=True, with_visit=True):
    session = DoctorPracticeSession(doctor_role_registration_id=doctor_registration.id, facility_id=facility.id, session_date=date.today(), status=SessionStatus.ACTIVE.value, started_at=datetime.now(UTC))
    appointment = Appointment(citizen_id=citizen.id, doctor_role_registration_id=doctor_registration.id, facility_id=facility.id, appointment_date=date.today(), serial_number=1, status=AppointmentStatus.BOOKED.value, booked_at=datetime.now(UTC))
    db.add_all([session, appointment]); db.flush()
    db.add(AppointmentQueueEntry(appointment_id=appointment.id, practice_session_id=session.id, queue_status=QueueStatus.CURRENT.value if current else QueueStatus.WAITING.value, became_current_at=datetime.now(UTC) if current else None))
    visit = None
    if with_visit:
        visit = MedicalVisit(citizen_id=citizen.id, doctor_role_registration_id=doctor_registration.id, facility_id=facility.id, appointment_id=appointment.id, status=VisitStatus.DRAFT.value)
        db.add(visit)
    db.commit()
    return visit


def test_current_doctor_creates_and_assigns_only_eligible_same_facility_technician(client: TestClient, db_session, test_settings: Settings):
    facility = _facility(db_session)
    other_facility = _facility(db_session, "Other Facility")
    doctor, doctor_registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    _, technician = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    _, cross_facility = _registration(db_session, other_facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    _, unverified = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN, verified=False)
    _, citizen = _citizen(db_session, "Patient")
    visit = _queue(db_session, doctor_registration, facility, citizen)
    token = _token(db_session, test_settings, doctor, Portal.PROFESSIONAL, doctor_registration)

    choices = client.get("/api/v1/professionals/diagnostic-technicians", headers=_auth(token))
    assert choices.status_code == 200
    assert [row["role_registration_id"] for row in choices.json()] == [str(technician.id)]
    created = client.post("/api/v1/professionals/current-patient/diagnostic-tests", headers=_auth(token), json={"visit_id": str(visit.id), "test_name": "Complete blood count", "instructions": "Fasting", "assigned_to_role_registration_id": str(technician.id)})
    assert created.status_code == 201, created.text
    assert created.json()["visit_id"] == str(visit.id)
    assert created.json()["status"] == "REQUESTED"

    for invalid in (cross_facility.id, unverified.id):
        denied = client.post("/api/v1/professionals/current-patient/diagnostic-tests", headers=_auth(token), json={"visit_id": str(visit.id), "test_name": "Invalid assignment", "assigned_to_role_registration_id": str(invalid)})
        assert denied.status_code == 422


def test_waiting_wrong_doctor_citizen_and_wrong_role_cannot_create(client: TestClient, db_session, test_settings: Settings):
    facility = _facility(db_session)
    doctor, doctor_registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    other_doctor, other_registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    lab_user, lab_registration = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    citizen_user, citizen = _citizen(db_session, "Waiting")
    visit = _queue(db_session, doctor_registration, facility, citizen, current=False)
    path = "/api/v1/professionals/current-patient/diagnostic-tests"
    assert client.post(path, headers=_auth(_token(db_session, test_settings, doctor, Portal.PROFESSIONAL, doctor_registration)), json={"visit_id": str(visit.id), "test_name": "CBC"}).status_code == 404
    assert client.post(path, headers=_auth(_token(db_session, test_settings, other_doctor, Portal.PROFESSIONAL, other_registration)), json={"visit_id": str(visit.id), "test_name": "CBC"}).status_code == 404
    assert client.post(path, headers=_auth(_token(db_session, test_settings, lab_user, Portal.PROFESSIONAL, lab_registration)), json={"visit_id": str(visit.id), "test_name": "CBC"}).status_code == 403
    assert client.post(path, headers=_auth(_token(db_session, test_settings, citizen_user, Portal.CITIZEN)), json={"visit_id": str(visit.id), "test_name": "CBC"}).status_code == 403


def test_transition_matrix_and_citizen_ownership(client: TestClient, db_session, test_settings: Settings):
    facility = _facility(db_session)
    doctor, doctor_registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    lab_user, lab_registration = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    other_user, other_citizen = _citizen(db_session, "Other")
    citizen_user, citizen = _citizen(db_session, "Owner")
    visit = _queue(db_session, doctor_registration, facility, citizen)
    doctor_token = _token(db_session, test_settings, doctor, Portal.PROFESSIONAL, doctor_registration)
    created = client.post("/api/v1/professionals/current-patient/diagnostic-tests", headers=_auth(doctor_token), json={"visit_id": str(visit.id), "test_name": "CBC", "assigned_to_role_registration_id": str(lab_registration.id)}).json()
    test_id = created["id"]
    lab_token = _token(db_session, test_settings, lab_user, Portal.PROFESSIONAL, lab_registration)
    base = f"/api/v1/professionals/me/diagnostic-tests/{test_id}/transitions"
    assert client.post(f"{base}/COMPLETED", headers=_auth(lab_token)).status_code == 409
    assert client.post(f"{base}/IN_PROGRESS", headers=_auth(lab_token)).json()["status"] == "IN_PROGRESS"
    assert client.put(f"/api/v1/professionals/me/diagnostic-tests/{test_id}/assignment", headers=_auth(doctor_token), json={"assigned_to_role_registration_id": None}).status_code == 409
    assert client.post(f"{base}/CANCELLED", headers=_auth(doctor_token)).status_code == 409
    assert client.post(f"{base}/COMPLETED", headers=_auth(lab_token)).status_code == 409
    assert client.post(f"{base}/IN_PROGRESS", headers=_auth(lab_token)).status_code == 409

    owner = client.get("/api/v1/citizens/me/diagnostic-tests", headers=_auth(_token(db_session, test_settings, citizen_user, Portal.CITIZEN))).json()
    other = client.get("/api/v1/citizens/me/diagnostic-tests", headers=_auth(_token(db_session, test_settings, other_user, Portal.CITIZEN))).json()
    assert [row["id"] for row in owner["tests"]] == [test_id]
    assert other == {"tests": []}
    assert db_session.scalar(select(DiagnosticTest).where(DiagnosticTest.id == uuid.UUID(test_id))).status == "IN_PROGRESS"


@pytest.mark.parametrize("change", ["queue", "session", "visit", "displayed_visit"])
def test_stale_consultation_never_creates_a_request(db_session, change):
    facility = _facility(db_session)
    doctor, registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    _, citizen = _citizen(db_session, "Stale")
    visit = _queue(db_session, registration, facility, citizen)
    context = VisitsRepository(db_session).load_current_patient_for_doctor(doctor.id)
    assert context
    payload = DiagnosticTestCreateRequest(visit_id=visit.id, test_name="CBC")
    if change == "queue":
        context.queue_entry.queue_status = QueueStatus.DONE.value
    elif change == "session":
        session = db_session.get(DoctorPracticeSession, context.queue_entry.practice_session_id)
        session.status = SessionStatus.COMPLETED.value
    elif change == "visit":
        visit.status = VisitStatus.FINALIZED.value
    else:
        payload.visit_id = uuid.uuid4()
    db_session.commit()
    with pytest.raises(HealthLinkError) as caught:
        DiagnosticsService(db_session).create(CurrentPatientAccess(context, "queue"), registration, payload)
    assert caught.value.status_code == 409
    assert list(db_session.scalars(select(DiagnosticTest))) == []


def test_assignment_search_uses_request_facility_and_hides_inactive_users(client, db_session, test_settings):
    facility = _facility(db_session)
    doctor, registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    lab_user, lab = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    _, citizen = _citizen(db_session, "Assignment")
    visit = _queue(db_session, registration, facility, citizen)
    token = _token(db_session, test_settings, doctor, Portal.PROFESSIONAL, registration)
    created = client.post("/api/v1/professionals/current-patient/diagnostic-tests", headers=_auth(token), json={"visit_id": str(visit.id), "test_name": "CBC"}).json()
    test_id = created["id"]
    registration.facility_id = _facility(db_session, "Moved doctor").id
    db_session.commit()
    choices = client.get(f"/api/v1/professionals/diagnostic-technicians?test_id={test_id}", headers=_auth(token))
    assert [row["role_registration_id"] for row in choices.json()] == [str(lab.id)]
    path = f"/api/v1/professionals/me/diagnostic-tests/{test_id}/assignment"
    assert client.put(path, headers=_auth(token), json={"assigned_to_role_registration_id": str(lab.id)}).status_code == 200
    lab_user.is_active = False
    db_session.commit()
    assert client.get(f"/api/v1/professionals/diagnostic-technicians?test_id={test_id}", headers=_auth(token)).json() == []
    assert client.put(path, headers=_auth(token), json={"assigned_to_role_registration_id": str(lab.id)}).status_code == 422
