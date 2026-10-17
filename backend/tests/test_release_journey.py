"""Synthetic HTTP-to-database acceptance across care, reports, dashboards and AI.

This complements component/browser checks; it is not a browser acceptance test.
"""
from sqlalchemy import func, select

from app.admins.models import AdminAccount
from app.appointments.models import Appointment, DoctorPracticeSession
from app.auth.constants import Portal
from app.clinical_audit.models import MedicalRecordAccessLog
from app.dashboards.service import care_today
from app.prescriptions.models import PrescriptionDocument
from app.professionals.constants import ProfessionalRoleCode
from test_ai_clinical_explanations import CapturingClinicalProvider, _client, _enabled
from test_diagnostics import _auth, _citizen, _facility, _queue, _registration, _token, _user
from test_lab_reports import payload as report_payload


def test_synthetic_care_to_finalized_results_and_explanations(db_session, test_settings):
    facility = _facility(db_session, "Synthetic acceptance hospital")
    doctor_user, doctor = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    lab_user, lab = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    citizen_user, citizen = _citizen(db_session, "SyntheticAcceptanceOwner")
    other_user, _ = _citizen(db_session, "UnrelatedCitizen")
    admin_user = _user(db_session, "SyntheticAdmin")
    db_session.add(AdminAccount(user_id=admin_user.id))
    visit = _queue(db_session, doctor, facility, citizen)
    session = db_session.scalar(select(DoctorPracticeSession))
    appointment = db_session.get(Appointment, visit.appointment_id)
    session.session_date = appointment.appointment_date = care_today()
    db_session.commit()
    actors = {name: _auth(_token(db_session, test_settings, user, portal, role))
        for name, user, portal, role in [
            ("doctor", doctor_user, Portal.PROFESSIONAL, doctor),
            ("lab", lab_user, Portal.PROFESSIONAL, lab),
            ("citizen", citizen_user, Portal.CITIZEN, None),
            ("other", other_user, Portal.CITIZEN, None),
            ("admin", admin_user, Portal.ADMIN, None),
        ]}
    provider = CapturingClinicalProvider()
    with _client(_enabled(test_settings), db_session, provider) as client:
        citizen_overview = "/api/v1/citizens/me/overview"
        professional_overview = "/api/v1/professionals/me/overview"
        initial = client.get(citizen_overview, headers=actors["citizen"]).json()
        assert initial["recent_prescription"] is None and initial["latest_report"] is None
        assert initial["upcoming_appointment"]["id"] == str(appointment.id)
        assert client.get(professional_overview, headers=actors["doctor"]).json()["chambers"][0]["current_serial"] == 1

        clinical = {"chief_complaint": "Synthetic source complaint", "clinical_notes": "Synthetic source note",
            "items": [{"medicine_name": "Medicine A", "dosage": "1 tablet", "frequency": "Daily", "duration": "5 days"}]}
        created = client.post(f"/api/v1/visits/{visit.id}/prescription", headers=actors["doctor"], json=clinical)
        assert created.status_code == 201, created.text
        prescription_id = created.json()["id"]
        assert client.get(citizen_overview, headers=actors["citizen"]).json()["recent_prescription"] is None

        diagnostic = client.post("/api/v1/professionals/current-patient/diagnostic-tests", headers=actors["doctor"],
            json={"visit_id": str(visit.id), "test_name": "Synthetic CBC", "assigned_to_role_registration_id": str(lab.id)})
        assert diagnostic.status_code == 201, diagnostic.text
        test_id = diagnostic.json()["id"]
        assert client.get(professional_overview, headers=actors["lab"]).json()["requested_tests"] == 1
        transition = f"/api/v1/professionals/me/diagnostic-tests/{test_id}/transitions/IN_PROGRESS"
        assert client.post(transition, headers=actors["lab"]).status_code == 200
        report_path = f"/api/v1/diagnostic-tests/{test_id}/lab-report"
        assert client.put(report_path, headers=actors["lab"], json=report_payload()).status_code == 200
        assert client.get(professional_overview, headers=actors["lab"]).json()["draft_reports"] == 1
        assert client.get(report_path, headers=actors["citizen"]).status_code == 404
        finalized = client.post(report_path + "/finalize", headers=actors["lab"])
        assert finalized.status_code == 200, finalized.text
        report_id = finalized.json()["id"]
        assert client.put(report_path, headers=actors["lab"], json=report_payload()).status_code == 409
        lab_overview = client.get(professional_overview, headers=actors["lab"]).json()
        assert lab_overview["draft_reports"] == 0 and lab_overview["finalized_reports"] == 1
        assert lab_overview["chambers"] == []
        assert client.get(citizen_overview, headers=actors["citizen"]).json()["latest_report"]["diagnostic_test_id"] == test_id
        assert len(client.get("/api/v1/citizens/me/lab-trends", headers=actors["citizen"]).json()) == 1
        assert client.get(report_path, headers=actors["other"]).status_code == 404

        finished = client.post(f"/api/v1/appointments/{appointment.id}/finish", headers=actors["doctor"])
        assert finished.status_code == 200, finished.text
        overview = client.get(citizen_overview, headers=actors["citizen"]).json()
        assert overview["upcoming_appointment"] is None
        assert overview["recent_prescription"]["id"] == prescription_id
        assert client.get(professional_overview, headers=actors["doctor"]).json()["chambers"][0]["current_serial"] is None
        assert client.get(professional_overview, headers=actors["doctor"]).json()["recent_prescription"]["id"] == prescription_id
        for _ in range(2):
            pdf = client.get(f"/api/v1/prescriptions/{prescription_id}/pdf", headers=actors["citizen"])
            assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
            assert pdf.headers["cache-control"] == "private, no-store"
        assert db_session.scalar(select(func.count()).select_from(PrescriptionDocument)) == 0

        prescription_explanation = client.post(f"/api/v1/ai/prescriptions/{prescription_id}/explain", headers=actors["citizen"])
        assert prescription_explanation.status_code == 200, prescription_explanation.text
        assert "1 tablet" in prescription_explanation.json()["medicine_explanations"][0]["recorded_instructions"]
        assert client.post(f"/api/v1/ai/lab-reports/{report_id}/explain", headers=actors["citizen"]).status_code == 200
        assert client.post(f"/api/v1/ai/lab-reports/{report_id}/explain", headers=actors["other"]).status_code == 404
        assert len(provider.prompts) == 2
        assert client.get("/api/v1/admin/overview", headers=actors["admin"]).json()["active_facilities"] == 1
        assert client.get(professional_overview, headers=actors["admin"]).status_code == 403
        assert client.get("/api/v1/admin/overview", headers=actors["citizen"]).status_code == 403
    assert db_session.scalar(select(func.count()).select_from(MedicalRecordAccessLog)
        .where(MedicalRecordAccessLog.action == "AI_ACCESS")) == 2
