from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.admins.models import AdminAccount
from app.appointments.models import Appointment, AppointmentQueueEntry, DoctorPracticeSession
from app.auth.constants import Portal
from app.auth.models import User
from app.clinical_audit.models import MedicalRecordAccessLog
from app.dashboards.service import care_today
from app.diagnostics.models import DiagnosticTest
from app.diagnostics.report_models import LabReport
from app.emergency.models import EmergencyProfile
from app.prescriptions.models import Prescription
from app.professionals.constants import ProfessionalRoleCode
from app.reminders.models import MedicineReminder
from test_medical_history import _auth, _citizen, _facility, _professional, _token, _user, _visit


PATHS = ["/api/v1/citizens/me/overview", "/api/v1/professionals/me/overview", "/api/v1/admin/overview"]


@pytest.mark.parametrize("path", PATHS)
def test_overviews_require_authentication(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("portal,allowed", [(Portal.CITIZEN, 0), (Portal.PROFESSIONAL, 1), (Portal.ADMIN, 2)])
def test_dashboard_portal_matrix(client, db_session, test_settings, portal, allowed):
    citizen = _citizen(db_session, "Owner")
    user = db_session.get(User, citizen.user_id)
    registration_id = None
    if portal is Portal.PROFESSIONAL:
        user, registration = _professional(db_session, _facility(db_session))
        registration_id = registration.id
    elif portal is Portal.ADMIN:
        user = _user(db_session, "Admin")
        db_session.add(AdminAccount(user_id=user.id))
        db_session.commit()
    token = _token(db_session, test_settings, user, portal, role_registration_id=registration_id)
    for index, path in enumerate(PATHS):
        response = client.get(path, headers=_auth(token))
        assert response.status_code == (200 if index == allowed else 403)
        assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("status", ["PENDING", "REJECTED"])
def test_unverified_professional_dashboard_is_denied(client, db_session, test_settings, status):
    user, registration = _professional(db_session, _facility(db_session))
    registration.verification_status = status
    registration.verified_at = None
    db_session.commit()
    token = _token(db_session, test_settings, user, Portal.PROFESSIONAL, role_registration_id=registration.id)
    assert client.get(PATHS[1], headers=_auth(token)).status_code == 403


def test_inactive_admin_cannot_load_operational_counts(client, db_session, test_settings):
    user = _user(db_session, "InactiveAdmin")
    db_session.add(AdminAccount(user_id=user.id, is_active=False))
    db_session.commit()
    token = _token(db_session, test_settings, user, Portal.ADMIN)
    assert client.get(PATHS[2], headers=_auth(token)).status_code == 403


def test_citizen_overview_minimized_owned_finalized_and_audited(client, db_session, test_settings):
    owner, stranger = _citizen(db_session, "Owner"), _citizen(db_session, "Stranger")
    facility = _facility(db_session)
    _, doctor = _professional(db_session, facility)
    _, lab = _professional(db_session, facility, role_code=ProfessionalRoleCode.LAB_TECHNICIAN)
    now, today = datetime.now(UTC), care_today()
    ids = {}
    for citizen, finalized in [(owner, True), (owner, False), (stranger, True)]:
        visit = _visit(db_session, citizen=citizen, registration=doctor, facility=facility,
                       finalized_at=now if finalized else None, diagnosis="PRIVATE CLINICAL TEXT")
        prescription = Prescription(visit_id=visit.id, citizen_id=citizen.id,
            author_doctor_role_registration_id=doctor.id, created_at=now + timedelta(seconds=len(ids)))
        db_session.add(prescription)
        db_session.flush()
        ids[(citizen.id, finalized)] = prescription.id
    test = DiagnosticTest(citizen_id=owner.id, requested_by_role_registration_id=doctor.id,
        assigned_to_role_registration_id=lab.id, facility_id=facility.id, test_name="Synthetic finalized test", status="COMPLETED")
    db_session.add(test)
    db_session.flush()
    db_session.add(LabReport(diagnostic_test_id=test.id, citizen_id=owner.id, facility_id=facility.id,
        created_by_role_registration_id=lab.id, report_date=today, status="FINALIZED", finalized_at=now))
    db_session.add(EmergencyProfile(citizen_id=owner.id, allergies="PRIVATE ALLERGY", emergency_contact_phone="PRIVATE PHONE"))
    for citizen, start, end, active in [(owner,today,None,True), (owner,today+timedelta(days=1),None,True),
        (owner,today-timedelta(days=5),today-timedelta(days=1),True), (owner,today,None,False), (stranger,today,None,True)]:
        db_session.add(MedicineReminder(citizen_id=citizen.id, medicine="PRIVATE MEDICINE", start_date=start, end_date=end, is_active=active))
    db_session.commit()
    token = _token(db_session, test_settings, db_session.get(User, owner.user_id), Portal.CITIZEN)
    response = client.get(f"{PATHS[0]}?citizen_id={stranger.id}", headers=_auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["recent_prescription"]["id"] == str(ids[(owner.id, True)])
    assert body["latest_report"]["diagnostic_test_id"] == str(test.id)
    assert body["active_reminders"] == 1
    assert body["emergency_profile_updated_at"]
    assert "PRIVATE" not in response.text
    audit = db_session.scalars(select(MedicalRecordAccessLog)).all()
    assert len(audit) == 1 and audit[0].citizen_id == owner.id
    assert audit[0].resource_type == "CARE_OVERVIEW"


def test_doctor_overview_reads_only_own_today_queue_without_patient_details(client, db_session, test_settings):
    facility, citizen = _facility(db_session), _citizen(db_session, "PrivatePatient")
    user, doctor = _professional(db_session, facility)
    _, other_doctor = _professional(db_session, facility)
    for registration in [doctor, other_doctor]:
        session = DoctorPracticeSession(doctor_role_registration_id=registration.id, facility_id=facility.id, session_date=care_today(), status="ACTIVE")
        db_session.add(session)
        db_session.flush()
        for number, status in [(1, "CURRENT"), (2, "WAITING")]:
            appointment = Appointment(citizen_id=citizen.id, doctor_role_registration_id=registration.id,
                facility_id=facility.id, appointment_date=care_today(), serial_number=number,
                status="BOOKED", booked_at=datetime.now(UTC), reason="PRIVATE REASON")
            db_session.add(appointment)
            db_session.flush()
            db_session.add(AppointmentQueueEntry(appointment_id=appointment.id, practice_session_id=session.id, queue_status=status))
    db_session.commit()
    token = _token(db_session, test_settings, user, Portal.PROFESSIONAL, role_registration_id=doctor.id)
    response = client.get(PATHS[1], headers=_auth(token))
    assert response.status_code == 200
    assert len(response.json()["chambers"]) == 1
    assert response.json()["chambers"][0]["waiting_count"] == 1
    assert response.json()["chambers"][0]["current_serial"] == 1
    assert "PRIVATE" not in response.text and str(citizen.id) not in response.text


def test_lab_overview_exact_role_assignment_facility_and_no_chamber(client, db_session, test_settings):
    facility, citizen = _facility(db_session), _citizen(db_session, "LabPatient")
    _, doctor = _professional(db_session, facility)
    user, lab = _professional(db_session, facility, role_code=ProfessionalRoleCode.LAB_TECHNICIAN)
    _, other_lab = _professional(db_session, facility, role_code=ProfessionalRoleCode.LAB_TECHNICIAN)
    for assignee, facility_id in [(lab.id,facility.id), (other_lab.id,facility.id), (lab.id,_facility(db_session).id), (None,facility.id)]:
        db_session.add(DiagnosticTest(citizen_id=citizen.id, requested_by_role_registration_id=doctor.id,
            assigned_to_role_registration_id=assignee, facility_id=facility_id, test_name="PRIVATE TEST"))
    db_session.commit()
    token = _token(db_session, test_settings, user, Portal.PROFESSIONAL, role_registration_id=lab.id)
    response = client.get(PATHS[1], headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["requested_tests"] == 1
    assert response.json()["chambers"] == [] and response.json()["recent_prescription"] is None
    tests_path = "/api/v1/professionals/me/diagnostic-tests"
    assert len(client.get(tests_path, headers=_auth(token)).json()["tests"]) == 1
    facility.is_active = False
    db_session.commit()
    assert client.get(PATHS[1], headers=_auth(token)).json()["requested_tests"] == 0
    assert client.get(tests_path, headers=_auth(token)).json()["tests"] == []


@pytest.mark.parametrize("state", ["CANCELLED", "WRONG_DOCTOR", "WRONG_FACILITY", "WRONG_DATE", "CLOSED_SESSION"])
def test_chamber_overview_ignores_stale_or_mismatched_queue_rows(client, db_session, test_settings, state):
    from test_diagnostics import _queue
    facility, citizen = _facility(db_session), _citizen(db_session, "QueueOwner")
    user, doctor = _professional(db_session, facility)
    _queue(db_session, doctor, facility, citizen, current=False)
    session = db_session.scalar(select(DoctorPracticeSession))
    appointment = db_session.scalar(select(Appointment))
    session.session_date = care_today()
    appointment.appointment_date = care_today()
    if state == "CANCELLED":
        appointment.status = "CANCELLED"
    elif state == "WRONG_DOCTOR":
        _, other = _professional(db_session, facility)
        appointment.doctor_role_registration_id = other.id
    elif state == "WRONG_FACILITY":
        appointment.facility_id = _facility(db_session).id
    elif state == "WRONG_DATE":
        appointment.appointment_date += timedelta(days=1)
    else:
        session.status = "COMPLETED"
    db_session.commit()
    token = _token(db_session, test_settings, user, Portal.PROFESSIONAL, role_registration_id=doctor.id)
    chamber = client.get(PATHS[1], headers=_auth(token)).json()["chambers"][0]
    assert chamber["waiting_count"] == 0 and chamber["current_serial"] is None


@pytest.mark.parametrize("path", ["/api/v1/auth/citizen/login", "/api/v1/auth/refresh"])
def test_auth_errors_are_not_cached_without_bearer(client, path):
    response = client.post(path, json={})
    assert response.status_code >= 400
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_diagnostic_pagination_is_bounded_and_complete(client, db_session, test_settings):
    facility, citizen = _facility(db_session), _citizen(db_session, "PagedPatient")
    _, doctor = _professional(db_session, facility)
    db_session.add_all(DiagnosticTest(citizen_id=citizen.id, requested_by_role_registration_id=doctor.id,
        facility_id=facility.id, test_name=f"Synthetic test {index}") for index in range(5))
    db_session.commit()
    token = _token(db_session, test_settings, db_session.get(User, citizen.user_id), Portal.CITIZEN)
    path, seen = "/api/v1/citizens/me/diagnostic-tests", []
    for page in range(1, 4):
        response = client.get(f"{path}?page={page}&page_size=2", headers=_auth(token))
        assert response.status_code == 200
        body = response.json()
        seen.extend(item["id"] for item in body["tests"])
        assert len(body["tests"]) <= 2 and body["has_next"] == (page < 3)
    assert len(seen) == len(set(seen)) == 5
    for query in ["page=0", "page_size=101", "page=10001"]:
        assert client.get(f"{path}?{query}", headers=_auth(token)).status_code == 422


@pytest.mark.parametrize("closed", ["SESSION", "APPOINTMENT"])
def test_stale_current_queue_does_not_expose_patient_after_closure(db_session, closed):
    from app.visits.repository import VisitsRepository
    from test_diagnostics import _queue
    facility, citizen = _facility(db_session), _citizen(db_session, "StalePatient")
    user, doctor = _professional(db_session, facility)
    _queue(db_session, doctor, facility, citizen)
    queue = db_session.scalar(select(AppointmentQueueEntry))
    if closed == "SESSION":
        db_session.get(DoctorPracticeSession, queue.practice_session_id).status = "COMPLETED"
    else:
        db_session.get(Appointment, queue.appointment_id).status = "CANCELLED"
    db_session.commit()
    repository = VisitsRepository(db_session)
    assert repository.load_current_patient_for_doctor(user.id) is None
    assert repository.load_queue_entry_for_doctor(user.id, queue.id) is None


def test_sql_errors_hide_bound_medical_values():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from app.db.session import create_database_engine
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection, pytest.raises(DBAPIError) as caught:
            connection.execute(text("SELECT * FROM missing_table WHERE notes=:notes"), {"notes": "PRIVATE CLINICAL VALUE"})
        assert "PRIVATE CLINICAL VALUE" not in str(caught.value)
        assert engine.hide_parameters
    finally:
        engine.dispose()


def test_validation_errors_do_not_echo_arbitrary_medical_free_text(test_settings):
    from fastapi.testclient import TestClient
    from pydantic import BaseModel, Field
    from app.main import create_app
    class Input(BaseModel):
        notes: str = Field(max_length=3)
    app = create_app(test_settings)
    @app.post("/_test/clinical-input")
    def submit(body: Input):
        return {}
    with TestClient(app) as local:
        response = local.post("/_test/clinical-input", json={"notes": "PRIVATE CLINICAL VALUE"})
    assert response.status_code == 422 and "PRIVATE CLINICAL VALUE" not in response.text


def test_private_admin_identity_search_uses_body_and_same_authority(client, db_session, test_settings):
    user, citizen = _user(db_session, "TrustedAdmin"), _citizen(db_session, "SearchedCitizen")
    db_session.add(AdminAccount(user_id=user.id))
    db_session.commit()
    token = _token(db_session, test_settings, user, Portal.ADMIN)
    path = "/api/v1/admin/citizen-identities/search"
    response = client.post(path, json={"user_id": str(citizen.user_id)}, headers=_auth(token))
    assert response.status_code == 200
    assert client.post(path, json={"user_id": str(citizen.user_id)}).status_code == 401
    assert client.post(path, json={"limit": 100}, headers=_auth(token)).status_code == 422
