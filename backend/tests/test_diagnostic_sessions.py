from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4

from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.admins.models import AdminAccount
from app.auth.constants import Portal
from app.clinical_audit.models import MedicalRecordAccessLog
from app.diagnostics.session_models import LabSession
from app.professionals.constants import ProfessionalRoleCode
from test_diagnostics import _auth, _citizen, _facility, _queue, _registration, _token, _user


CITIZEN = "/api/v1/citizens/me/diagnostic-sessions"
LAB = "/api/v1/professionals/me/diagnostic-sessions"
REQUESTS = "/api/v1/professionals/current-patient/diagnostic-tests"


def sample_pdf():
    buffer = BytesIO()
    report = canvas.Canvas(buffer)
    report.drawString(72, 720, "Synthetic diagnostic report")
    report.save()
    return buffer.getvalue()


def headers(db, settings, user, portal, role=None):
    return _auth(_token(db, settings, user, portal, role))


def create_session(client, owner, code):
    session_id = str(uuid4())
    response = client.post(CITIZEN, headers=owner, json={"id": session_id, "catalog_code": code})
    assert response.status_code == 201, response.text
    return response.json()


def claim(client, lab, session):
    result = client.post(LAB + "/accept", headers=lab, json={
        "code": session["share_code"],
        "attendance_deadline": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    })
    assert result.status_code == 200, result.text
    return result.json()


def test_cross_facility_pdf_is_private_and_fulfills_only_matching_requests(client, db_session, test_settings, monkeypatch):
    clinic = _facility(db_session, "Doctor clinic")
    facility = _facility(db_session, "Independent lab")
    doctor_user, doctor = _registration(db_session, clinic, ProfessionalRoleCode.DOCTOR)
    other_doctor, other_role = _registration(db_session, clinic, ProfessionalRoleCode.DOCTOR)
    technician, lab = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    patient_user, patient = _citizen(db_session, "Patient")
    other_patient, _ = _citizen(db_session, "Other patient")
    visit = _queue(db_session, doctor, clinic, patient)
    requester = headers(db_session, test_settings, doctor_user, Portal.PROFESSIONAL, doctor)
    ungranted = headers(db_session, test_settings, other_doctor, Portal.PROFESSIONAL, other_role)
    owner = headers(db_session, test_settings, patient_user, Portal.CITIZEN)
    outsider = headers(db_session, test_settings, other_patient, Portal.CITIZEN)
    lab_auth = headers(db_session, test_settings, technician, Portal.PROFESSIONAL, lab)

    def request(code):
        result = client.post(REQUESTS, headers=requester, json={"visit_id": str(visit.id), "catalog_code": code})
        assert result.status_code == 201, result.text
        return result.json()

    older = request("CBC")
    unrelated = request("LIPID_PANEL")
    assert older["facility_id"] is None and older["assigned_to_role_registration_id"] is None
    session = create_session(client, owner, "CBC")
    accepted = claim(client, lab_auth, session)
    assert accepted["facility_name"] == "Independent lab" and accepted["share_code"] is None
    assert client.post(f"{CITIZEN}/{session['id']}/cancel", headers=owner).status_code == 409
    lab_path = f"{LAB}/{session['id']}"
    pdf_path = f"/api/v1/diagnostic-sessions/{session['id']}/pdf"
    for step in ("CHECKED_IN", "COLLECTED", "PERFORMED"):
        assert client.post(f"{lab_path}/steps/{step}", headers=lab_auth).status_code == 200
    later = request("CBC")
    upload_headers = {**lab_auth, "Content-Type": "application/pdf"}
    pdf = sample_pdf()
    settings = client.app.state.settings
    monkeypatch.setattr(settings, "diagnostic_clamav_host", "")
    assert client.put(lab_path + "/pdf", headers=upload_headers, content=b"not a PDF").status_code == 422

    def scanner_unavailable(*args, **kwargs):
        raise OSError("Synthetic scanner outage")

    with monkeypatch.context() as scanner:
        scanner.setattr(settings, "diagnostic_clamav_host", "scanner.invalid")
        scanner.setattr("app.diagnostics.pdf_screening.socket.create_connection", scanner_unavailable)
        assert client.put(lab_path + "/pdf", headers=upload_headers, content=pdf).status_code == 503

    draft = client.put(lab_path + "/pdf", headers=upload_headers, content=pdf)
    assert draft.status_code == 200, draft.text
    version = draft.json()["draft_version"]
    audit = db_session.scalar(select(MedicalRecordAccessLog.action).where(
        MedicalRecordAccessLog.resource_id == UUID(session["id"]),
        MedicalRecordAccessLog.action.in_(("UPLOAD_PDF", "SCREENED_PDF")),
    ))
    assert audit == "UPLOAD_PDF"
    assert client.get(pdf_path, headers=owner).status_code == 404
    assert client.get(f"{lab_path}/pdf/{version}", headers=lab_auth).content == pdf
    assert client.post(lab_path + "/publish", headers=lab_auth, json={"version": version}).status_code == 200

    def requests():
        return {item["id"]: item for item in client.get("/api/v1/citizens/me/diagnostic-tests", headers=owner).json()["tests"]}

    rows = requests()
    assert rows[older["id"]]["result_session_id"] == session["id"]
    assert rows[later["id"]]["status"] == rows[unrelated["id"]]["status"] == "REQUESTED"
    assert client.get("/api/v1/citizens/me/overview", headers=owner).json()["latest_report"]["is_pdf"] is True
    assert client.get("/api/v1/professionals/me/overview", headers=requester).json()["requested_tests"] == 2
    assert client.get("/api/v1/professionals/me/overview", headers=lab_auth).json()["finalized_reports"] == 1
    for actor in (owner, requester):
        read = client.get(pdf_path, headers=actor)
        assert read.status_code == 200 and read.content == pdf
        assert read.headers["cache-control"] == "private, no-store"
    for actor in (outsider, ungranted):
        assert client.get(pdf_path, headers=actor).status_code == 404
    history = client.get(f"/api/v1/professionals/patients/{patient.id}/medical-history?record_type=LAB_REPORT", headers=requester)
    assert history.status_code == 200, history.text
    assert history.json()["records"][0]["detail_url"].endswith(f"/{session['id']}/pdf")

    corrected = client.put(lab_path + "/pdf?catalog_code=LIPID_PANEL", headers=upload_headers, content=pdf)
    revision = corrected.json()["draft_version"]
    assert client.post(lab_path + "/publish", headers=lab_auth, json={"version": revision}).status_code == 200
    assert requests()[older["id"]]["status"] == "REQUESTED"
    assert requests()[unrelated["id"]]["result_session_id"] == session["id"]
    assert client.post(lab_path + "/withdraw", headers=lab_auth, json={"version": revision}).status_code == 200
    assert client.get(pdf_path, headers=owner).status_code == 404
    assert requests()[unrelated["id"]]["status"] == "REQUESTED"


def test_expiry_and_authorized_facility_recovery_require_fresh_sessions(client, db_session, test_settings):
    facility = _facility(db_session)
    patient, _ = _citizen(db_session, "Patient")
    technician, lab = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    admin_user = _user(db_session, "Admin")
    db_session.add(AdminAccount(user_id=admin_user.id, is_super_admin=True))
    db_session.commit()
    owner = headers(db_session, test_settings, patient, Portal.CITIZEN)
    lab_auth = headers(db_session, test_settings, technician, Portal.PROFESSIONAL, lab)
    admin = headers(db_session, test_settings, admin_user, Portal.ADMIN)

    expired = create_session(client, owner, "URINALYSIS")
    claim(client, lab_auth, expired)
    item = db_session.get(LabSession, UUID(expired["id"]))
    item.attendance_deadline = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    assert client.post(f"{LAB}/{expired['id']}/steps/CHECKED_IN", headers=lab_auth).status_code == 409
    assert client.get(CITIZEN, headers=owner).json()[0]["status"] == "EXPIRED"

    current = create_session(client, owner, "URINALYSIS")
    claim(client, lab_auth, current)
    recover = f"/api/v1/admin/facilities/{facility.id}/diagnostic-sessions"
    assert client.get(recover, headers=admin).json()["sessions"][0]["id"] == current["id"]
    assert client.post(f"{recover}/{current['id']}/close", headers=admin, json={"reason": "STAFF"}).status_code == 204
    rows = client.get(CITIZEN, headers=owner).json()
    assert rows[0]["status"] == "UNABLE" and rows[0]["closed_reason"] == "STAFF"
    assert rows[1]["status"] == "EXPIRED"
    assert client.post(f"{LAB}/{current['id']}/publish", headers=lab_auth, json={"version": 1}).status_code == 409
    assert create_session(client, owner, "URINALYSIS")["id"] not in {expired["id"], current["id"]}
