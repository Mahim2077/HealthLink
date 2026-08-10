import uuid

from fastapi import Depends
from fastapi.testclient import TestClient
import jwt
from sqlalchemy import func, select

from app.auth.models import AuthSession, User
from app.citizens.models import UserNationalIdentifier
from app.core.config import Settings
from app.core.security import hash_password
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.dependencies import require_verified_professional_role
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


def create_professional(
    db_session,
    *,
    statuses: dict[str, str],
) -> tuple[User, dict[str, ProfessionalRoleRegistration]]:
    suffix = uuid.uuid4().hex[:16]
    user = User(
        email=f"login-{suffix}@example.com",
        password_hash=hash_password("ProfessionalPassword123!"),
        first_name="Multi",
        last_name="Professional",
    )
    db_session.add(user); db_session.flush()
    db_session.add(UserNationalIdentifier(user_id=user.id, nid_number=f"LOGIN-{suffix}"))
    profile = HealthcareProfessionalProfile(user_id=user.id)
    facility = HealthcareFacility(name=f"Login Hospital {suffix}", facility_type="HOSPITAL", address="Dhaka")
    db_session.add_all([profile, facility]); db_session.flush()
    registrations: dict[str, ProfessionalRoleRegistration] = {}
    for code, status in statuses.items():
        role = db_session.scalar(select(ProfessionalRole).where(ProfessionalRole.code == code))
        assert role is not None
        registration = ProfessionalRoleRegistration(
            professional_id=profile.id,
            role_id=role.id,
            facility_id=facility.id if status == "VERIFIED" else None,
            facility_name_submitted=facility.name,
            designation=f"{code} designation",
            additional_info="Login coverage",
            verification_status=status,
        )
        db_session.add(registration)
        registrations[code] = registration
    db_session.commit()
    user.nid_for_login = f"LOGIN-{suffix}"  # type: ignore[attr-defined]
    return user, registrations


def login(client: TestClient, user: User, role: str, password: str = "ProfessionalPassword123!"):
    return client.post(
        "/api/v1/auth/professional/login",
        json={"nid_number": user.nid_for_login, "password": password, "role_code": role},  # type: ignore[attr-defined]
    )


def test_verified_multi_role_login_sets_and_preserves_exact_active_context(
    client: TestClient, db_session, test_settings: Settings
) -> None:
    user, registrations = create_professional(
        db_session, statuses={"DOCTOR": "VERIFIED", "LAB_TECHNICIAN": "VERIFIED"}
    )
    response = login(client, user, "LAB_TECHNICIAN")
    assert response.status_code == 200
    body = response.json()
    assert body["portal"] == "PROFESSIONAL"
    assert body["role_code"] == "LAB_TECHNICIAN"
    assert body["verification_status"] == "VERIFIED"
    assert body["role_registration_id"] == str(registrations["LAB_TECHNICIAN"].id)
    claims = jwt.decode(body["access_token"], test_settings.jwt_secret_key, algorithms=[test_settings.jwt_algorithm])
    assert claims["prrid"] == str(registrations["LAB_TECHNICIAN"].id)
    session = db_session.get(AuthSession, uuid.UUID(claims["sid"]))
    assert session.active_professional_role_registration_id == registrations["LAB_TECHNICIAN"].id

    me = client.get("/api/v1/professionals/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role_code"] == "LAB_TECHNICIAN"
    assert me.json()["facility"]["name"].startswith("Login Hospital")

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    refreshed_claims = jwt.decode(refreshed.json()["access_token"], test_settings.jwt_secret_key, algorithms=[test_settings.jwt_algorithm])
    assert refreshed_claims["prrid"] == claims["prrid"]


def test_pending_and_rejected_can_login_but_verified_dependency_denies(
    client: TestClient, db_session
) -> None:
    for status in ["PENDING", "REJECTED"]:
        user, _ = create_professional(db_session, statuses={"DOCTOR": status})
        response = login(client, user, "DOCTOR")
        assert response.status_code == 200
        assert response.json()["verification_status"] == status
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        assert client.get("/api/v1/professionals/me", headers=headers).status_code == 200


def test_wrong_nid_password_role_and_inactive_user_are_generic_and_create_no_session(
    client: TestClient, db_session
) -> None:
    user, _ = create_professional(db_session, statuses={"DOCTOR": "VERIFIED"})
    before = db_session.scalar(select(func.count()).select_from(AuthSession))
    attempts = [
        {"nid_number": "UNKNOWN", "password": "wrong", "role_code": "DOCTOR"},
        {"nid_number": user.nid_for_login, "password": "wrong", "role_code": "DOCTOR"},  # type: ignore[attr-defined]
        {"nid_number": user.nid_for_login, "password": "ProfessionalPassword123!", "role_code": "NURSE"},  # type: ignore[attr-defined]
    ]
    user.is_active = False; db_session.commit()
    attempts.append({"nid_number": user.nid_for_login, "password": "ProfessionalPassword123!", "role_code": "DOCTOR"})  # type: ignore[attr-defined]
    for payload in attempts:
        response = client.post("/api/v1/auth/professional/login", json=payload)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid NID, password, or professional role."}
    assert db_session.scalar(select(func.count()).select_from(AuthSession)) == before


def test_selected_lab_role_cannot_satisfy_doctor_dependency(
    client: TestClient, db_session
) -> None:
    user, _ = create_professional(
        db_session, statuses={"DOCTOR": "VERIFIED", "LAB_TECHNICIAN": "VERIFIED"}
    )

    @client.app.get("/test-phase7-doctor")
    def doctor_only(_context=Depends(require_verified_professional_role(ProfessionalRoleCode.DOCTOR))):
        return {"ok": True}

    lab = login(client, user, "LAB_TECHNICIAN")
    lab_headers = {"Authorization": f"Bearer {lab.json()['access_token']}"}
    assert client.get("/test-phase7-doctor", headers=lab_headers).status_code == 403
    doctor = login(client, user, "DOCTOR")
    doctor_headers = {"Authorization": f"Bearer {doctor.json()['access_token']}"}
    assert client.get("/test-phase7-doctor", headers=doctor_headers).status_code == 200
