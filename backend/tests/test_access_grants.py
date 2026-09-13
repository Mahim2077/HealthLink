from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import select

from app.access.policy import ClinicalReadPolicy, SCOPE_RESOURCES
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext
from app.clinical_audit.models import MedicalRecordAccessLog
from app.core.exceptions import HealthLinkError
from app.professionals.constants import ProfessionalRoleCode
from app.visits.models import PatientAccessGrant
from test_diagnostics import _auth, _citizen, _facility, _queue, _registration, _token


def context(user, registration=None):
    role_id = registration.id if registration else None
    return AuthContext(user=user, portal=Portal.PROFESSIONAL if registration else Portal.CITIZEN,
        session=SimpleNamespace(active_professional_role_registration_id=role_id),
        claims=SimpleNamespace(active_professional_role_registration_id=role_id))


@pytest.mark.parametrize("scope", list(SCOPE_RESOURCES))
@pytest.mark.parametrize("resource", ["VISIT", "PRESCRIPTION", "LAB_REPORT", "EMERGENCY_PROFILE", "MEDICAL_HISTORY"])
def test_every_scope_resource_pair(db_session, scope, resource):
    facility = _facility(db_session)
    user, role = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    _, citizen = _citizen(db_session, "Scope owner")
    grant = PatientAccessGrant(citizen_id=citizen.id, professional_role_registration_id=role.id,
        access_scope=scope, granted_at=datetime.now(UTC))
    db_session.add(grant); db_session.commit()
    policy = ClinicalReadPolicy(db_session)
    if resource in SCOPE_RESOURCES[scope]:
        decision = policy.authorize(context(user, role), citizen.id, resource)
        assert decision.source == "GRANT" and decision.grant_id == grant.id
    else:
        with pytest.raises(HealthLinkError) as exc:
            policy.authorize(context(user, role), citizen.id, resource)
        assert exc.value.status_code == 404


@pytest.mark.parametrize("state", ["expired", "revoked", "wrong_citizen", "wrong_role", "unverified", "inactive", "draft", "stale_claim"])
def test_grants_never_bypass_security(db_session, state):
    facility = _facility(db_session)
    user, role = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN if state == "wrong_role" else ProfessionalRoleCode.DOCTOR, verified=state != "unverified")
    _, citizen = _citizen(db_session, "Owner")
    _, other = _citizen(db_session, "Other")
    grant = PatientAccessGrant(citizen_id=citizen.id, professional_role_registration_id=role.id,
        access_scope="FULL_MEDICAL_HISTORY", granted_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) - timedelta(seconds=1) if state == "expired" else None,
        revoked_at=datetime.now(UTC) if state == "revoked" else None)
    if state == "inactive": user.is_active = False
    db_session.add(grant); db_session.commit()
    auth = context(user, role)
    if state == "stale_claim": auth.claims.active_professional_role_registration_id = uuid.uuid4()
    with pytest.raises(HealthLinkError):
        ClinicalReadPolicy(db_session).authorize(auth, other.id if state == "wrong_citizen" else citizen.id, "VISIT", finalized=state != "draft")


def test_current_relationship_and_specific_authorship(db_session):
    from app.appointments.models import DoctorPracticeSession
    facility = _facility(db_session)
    user, role = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    _, citizen = _citizen(db_session, "Current")
    visit = _queue(db_session, role, facility, citizen)
    policy = ClinicalReadPolicy(db_session)
    assert policy.authorize(context(user, role), citizen.id, "MEDICAL_HISTORY").source == "CURRENT_PATIENT"
    session = db_session.scalar(select(DoctorPracticeSession))
    session.status = "COMPLETED"; db_session.commit()
    with pytest.raises(HealthLinkError): policy.authorize(context(user, role), citizen.id, "MEDICAL_HISTORY")
    assert policy.authorize(context(user, role), citizen.id, "VISIT", resource_id=visit.id, author_role_id=role.id).source == "AUTHOR"
    with pytest.raises(HealthLinkError): policy.authorize(context(user, role), citizen.id, "VISIT", author_role_id=role.id)


def test_citizen_grant_lifecycle_selector_and_audit(client, db_session, test_settings):
    facility = _facility(db_session)
    doctor, role = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    _, lab = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    user, citizen = _citizen(db_session, "Grant owner")
    other, _ = _citizen(db_session, "Other owner")
    headers = _auth(_token(db_session, test_settings, user, Portal.CITIZEN))
    choices = client.get("/api/v1/citizens/me/access-grant-professionals", headers=headers)
    assert choices.status_code == 200
    assert [row["id"] for row in choices.json()] == [str(role.id)]
    assert "nid" not in choices.text.lower()
    path = "/api/v1/citizens/me/access-grants"
    payload = {"professional_role_registration_id": str(role.id), "access_scope": "VISITS_ONLY"}
    created = client.post(path, headers=headers, json=payload)
    assert created.status_code == 201, created.text
    assert client.post(path, headers=headers, json=payload).status_code == 409
    assert client.post(path, headers=headers, json={**payload, "professional_role_registration_id": str(lab.id)}).status_code == 422
    assert client.post(path, headers=headers, json={**payload, "expires_at": "2020-01-01T00:00:00Z"}).status_code == 422
    grant_id = created.json()["id"]
    other_headers = _auth(_token(db_session, test_settings, other, Portal.CITIZEN))
    assert client.post(f"{path}/{grant_id}/revoke", headers=other_headers).status_code == 404
    doctor_headers = _auth(_token(db_session, test_settings, doctor, Portal.PROFESSIONAL, role))
    assert client.get("/api/v1/professionals/me/access-grants", headers=doctor_headers).json()["grants"][0]["citizen_id"] == str(citizen.id)
    assert client.post(f"{path}/{grant_id}/revoke", headers=headers).json()["active"] is False
    assert client.post(f"{path}/{grant_id}/revoke", headers=headers).status_code == 200
    assert client.get("/api/v1/professionals/me/access-grants", headers=doctor_headers).json()["grants"] == []
    assert [row.action for row in db_session.scalars(select(MedicalRecordAccessLog).order_by(MedicalRecordAccessLog.created_at))] == ["GRANT", "REVOKE"]


def test_scoped_routes_exclude_drafts_and_grant_cannot_mutate(client, db_session, test_settings):
    facility = _facility(db_session)
    author, author_role = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    doctor, role = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    user, citizen = _citizen(db_session, "Shared owner")
    visit = _queue(db_session, author_role, facility, citizen)
    grant = PatientAccessGrant(citizen_id=citizen.id, professional_role_registration_id=role.id, access_scope="VISITS_ONLY", granted_at=datetime.now(UTC))
    db_session.add(grant); db_session.commit()
    headers = _auth(_token(db_session, test_settings, doctor, Portal.PROFESSIONAL, role))
    base = f"/api/v1/professionals/patients/{citizen.id}"
    assert client.get(f"{base}/medical-history?record_type=VISIT", headers=headers).json()["records"] == []
    assert client.get(f"{base}/medical-history", headers=headers).status_code == 404
    assert client.get(f"{base}/emergency-profile", headers=headers).status_code == 404
    assert client.get(f"{base}/visits/{visit.id}", headers=headers).status_code == 404
    visit.status = "FINALIZED"; visit.finalized_at = datetime.now(UTC); visit.clinical_notes = "Authorized clinical notes"
    db_session.commit()
    assert len(client.get(f"{base}/medical-history?record_type=VISIT", headers=headers).json()["records"]) == 1
    assert client.get(f"{base}/visits/{visit.id}", headers=headers).json()["clinical_notes"] == "Authorized clinical notes"
    denied = client.post("/api/v1/professionals/current-patient/diagnostic-tests", headers=headers, json={"visit_id": str(visit.id), "test_name": "Forbidden"})
    assert denied.status_code == 404
