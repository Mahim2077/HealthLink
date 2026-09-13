from sqlalchemy import select

from app.auth.constants import Portal
from app.clinical_audit.models import MedicalRecordAccessLog
from app.professionals.constants import ProfessionalRoleCode
from test_diagnostics import _auth, _citizen, _facility, _queue, _registration, _token


def test_current_read_is_audited_and_history_is_owner_only(client, db_session, test_settings):
    facility = _facility(db_session)
    doctor, role = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    owner, citizen = _citizen(db_session, "AuditOwner")
    stranger, _ = _citizen(db_session, "AuditStranger")
    _queue(db_session, role, facility, citizen)
    professional_headers = _auth(_token(db_session, test_settings, doctor, Portal.PROFESSIONAL, role))
    path = f"/api/v1/professionals/current-patient/emergency-profile?citizen_id={citizen.id}"
    assert client.get(path, headers=professional_headers).status_code == 200
    event = db_session.scalar(select(MedicalRecordAccessLog))
    assert event.actor_user_id == doctor.id
    assert event.citizen_id == citizen.id
    assert event.resource_type == "EMERGENCY_PROFILE"
    assert event.access_source == "CURRENT_PATIENT"
    history = "/api/v1/citizens/me/access-history"
    response = client.get(history, headers=_auth(_token(db_session, test_settings, owner, Portal.CITIZEN)))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert len(response.json()["items"]) == 1
    assert "allergies" not in response.text
    assert "nid" not in response.text.lower()
    assert client.get(history, headers=_auth(_token(db_session, test_settings, stranger, Portal.CITIZEN))).json()["items"] == []
    assert client.get(history, headers=professional_headers).status_code == 403
    assert client.get(history).status_code == 401
    assert client.get(history + "?page=0", headers=_auth(_token(db_session, test_settings, owner, Portal.CITIZEN))).status_code == 422
