import uuid

from sqlalchemy import select

from app.auth.constants import Portal
from app.emergency.models import EmergencyProfile
from app.professionals.constants import ProfessionalRoleCode
from test_diagnostics import _auth, _citizen, _facility, _queue, _registration, _token


def test_citizen_upserts_own_profile_without_copying_blood_group(client, db_session, test_settings):
    owner, citizen = _citizen(db_session, "EmergencyOwner")
    other, _ = _citizen(db_session, "EmergencyOther")
    citizen.blood_group = "O+"
    db_session.commit()
    headers = _auth(_token(db_session, test_settings, owner, Portal.CITIZEN))
    path = "/api/v1/citizens/me/emergency-profile"
    empty = client.get(path, headers=headers)
    assert empty.status_code == 200
    assert empty.json()["blood_group"] == "O+"
    assert empty.json()["updated_at"] is None
    saved = client.put(path, headers=headers, json={"allergies": " Penicillin ", "emergency_contact_phone": "+880 1700000000"})
    assert saved.status_code == 200
    assert saved.json()["allergies"] == "Penicillin"
    assert saved.json()["updated_at"] is not None
    changed = client.put(path, headers=headers, json={"allergies": " ", "special_notes": "Updated"})
    assert changed.json()["allergies"] is None
    assert len(list(db_session.scalars(select(EmergencyProfile)))) == 1
    citizen.blood_group = "AB+"
    db_session.commit()
    assert client.get(path, headers=headers).json()["blood_group"] == "AB+"
    assert client.get(path, headers=_auth(_token(db_session, test_settings, other, Portal.CITIZEN))).json()["special_notes"] is None
    assert client.put(path, headers=headers, json={"blood_group": "A+"}).status_code == 422
    assert client.put(path, headers=headers, json={"citizen_id": str(uuid.uuid4())}).status_code == 422
    assert client.put(path, headers=headers, json={"allergies": "a" * 4001}).status_code == 422


def test_only_current_verified_doctor_can_read_and_never_write(client, db_session, test_settings):
    facility = _facility(db_session)
    doctor, registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    other_doctor, other_registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR)
    lab, lab_registration = _registration(db_session, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
    unverified, unverified_registration = _registration(db_session, facility, ProfessionalRoleCode.DOCTOR, verified=False)
    citizen_user, citizen = _citizen(db_session, "CurrentEmergency")
    _queue(db_session, registration, facility, citizen)
    db_session.add(EmergencyProfile(citizen_id=citizen.id, allergies="Latex"))
    db_session.commit()
    path = f"/api/v1/professionals/current-patient/emergency-profile?citizen_id={citizen.id}"
    doctor_headers = _auth(_token(db_session, test_settings, doctor, Portal.PROFESSIONAL, registration))
    response = client.get(path, headers=doctor_headers)
    assert response.status_code == 200
    assert response.json()["allergies"] == "Latex"
    assert client.get(path.replace(str(citizen.id), str(uuid.uuid4())), headers=doctor_headers).status_code == 404
    for user, role, status in [(other_doctor, other_registration, 404), (lab, lab_registration, 403), (unverified, unverified_registration, 403)]:
        assert client.get(path, headers=_auth(_token(db_session, test_settings, user, Portal.PROFESSIONAL, role))).status_code == status
    assert client.get(path, headers=_auth(_token(db_session, test_settings, citizen_user, Portal.CITIZEN))).status_code == 403
    assert client.get(path).status_code == 401
    assert client.put(path, headers=doctor_headers, json={"allergies": "Changed"}).status_code == 405
    assert client.put("/api/v1/citizens/me/emergency-profile", headers=doctor_headers, json={}).status_code == 403
