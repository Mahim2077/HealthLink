from collections.abc import Callable
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.models import AuthSession, User
from app.citizens.models import UserNationalIdentifier
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)
from app.core.security import verify_password


def professional_payload(
    *,
    email: str = "doctor@example.com",
    nid_number: str = "P4-NID-0001",
    role_code: str = "DOCTOR",
    bmdc_registration_number: str | None = "BMDC-0001",
) -> dict[str, object]:
    return {
        "email": email,
        "password": "StrongPassword123!",
        "first_name": "Farhana",
        "last_name": "Ahmed",
        "nid_number": nid_number,
        "role_code": role_code,
        "facility_name": "Dhaka Medical College Hospital",
        "designation": "Consultant",
        "additional_info": "Internal medicine practitioner with ten years of experience.",
        "bmdc_registration_number": bmdc_registration_number,
    }


def citizen_payload(
    *,
    email: str,
    nid_number: str | None,
    bcn: str | None = None,
) -> dict[str, object]:
    return {
        "email": email,
        "password": "StrongPassword123!",
        "first_name": "Existing",
        "last_name": "Citizen",
        "date_of_birth": "1990-01-01",
        "gender": "OTHER",
        "nid_number": nid_number,
        "birth_certificate_number": bcn,
    }


def login_citizen(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": email, "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def onboarding_payload(
    *,
    role_code: str = "LAB_TECHNICIAN",
    bmdc: str | None = None,
) -> dict[str, object]:
    return {
        "role_code": role_code,
        "facility_name": "National Diagnostic Centre",
        "designation": "Senior Technologist",
        "additional_info": "Experienced diagnostic laboratory professional.",
        "bmdc_registration_number": bmdc,
    }


def test_new_doctor_registration_creates_pending_application_transactionally(
    client: TestClient,
    db_session,
) -> None:
    response = client.post(
        "/api/v1/auth/professional/register",
        json=professional_payload(email=" Doctor@Example.COM "),
    )

    assert response.status_code == 201
    assert response.json()["role_code"] == "DOCTOR"
    assert response.json()["verification_status"] == "PENDING"
    assert "nid_number" not in response.json()
    assert "bmdc_registration_number" not in response.json()
    assert not client.cookies
    user = db_session.get(User, uuid.UUID(response.json()["user_id"]))
    assert user is not None
    assert user.email == "doctor@example.com"
    assert verify_password("StrongPassword123!", user.password_hash)
    assert db_session.scalar(
        select(UserNationalIdentifier).where(UserNationalIdentifier.user_id == user.id)
    ).nid_number == "P4-NID-0001"
    registration = db_session.get(
        ProfessionalRoleRegistration,
        uuid.UUID(response.json()["role_registration_id"]),
    )
    assert registration is not None
    assert registration.verification_status == "PENDING"
    assert registration.verified_at is None
    assert registration.rejected_at is None
    assert db_session.scalar(
        select(DoctorRegistrationDetail).where(
            DoctorRegistrationDetail.professional_role_registration_id
            == registration.id
        )
    ).bmdc_registration_number == "BMDC-0001"
    assert db_session.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_non_doctor_registration_has_no_bmdc_detail(
    client: TestClient,
    db_session,
) -> None:
    response = client.post(
        "/api/v1/auth/professional/register",
        json=professional_payload(
            email="lab@example.com",
            nid_number="LAB-NID-1",
            role_code="LAB_TECHNICIAN",
            bmdc_registration_number=None,
        ),
    )
    assert response.status_code == 201
    assert response.json()["role_code"] == "LAB_TECHNICIAN"
    assert db_session.scalar(select(func.count()).select_from(DoctorRegistrationDetail)) == 0


def test_registration_validates_nid_role_fields_and_bmdc_rules(client: TestClient) -> None:
    no_nid = professional_payload()
    no_nid.pop("nid_number")
    no_bmdc = professional_payload()
    no_bmdc["bmdc_registration_number"] = None
    non_doctor_bmdc = professional_payload(
        role_code="NURSE",
        bmdc_registration_number="SHOULD-NOT-APPLY",
    )
    unknown_role = professional_payload(role_code="UNKNOWN")

    for payload in [no_nid, no_bmdc, non_doctor_bmdc, unknown_role]:
        assert client.post(
            "/api/v1/auth/professional/register", json=payload
        ).status_code == 422


def test_existing_nid_requires_authenticated_onboarding_without_duplicate_user(
    client: TestClient,
    db_session,
) -> None:
    registration = client.post(
        "/api/v1/auth/citizen/register",
        json=citizen_payload(email="citizen-pro@example.com", nid_number="SHARED-NID"),
    )
    existing_user_id = uuid.UUID(registration.json()["user_id"])
    users_before = db_session.scalar(select(func.count()).select_from(User))

    duplicate = client.post(
        "/api/v1/auth/professional/register",
        json=professional_payload(
            email="duplicate-person@example.com",
            nid_number="SHARED-NID",
        ),
    )
    assert duplicate.status_code == 409
    assert "onboarding" in duplicate.json()["detail"].lower()
    same_account = client.post(
        "/api/v1/auth/professional/register",
        json=professional_payload(
            email="citizen-pro@example.com",
            nid_number="SHARED-NID",
        ),
    )
    assert same_account.status_code == 409
    assert "onboarding" in same_account.json()["detail"].lower()
    assert db_session.scalar(select(func.count()).select_from(User)) == users_before

    token = login_citizen(client, "citizen-pro@example.com")
    onboarded = client.post(
        "/api/v1/professionals/me/onboard",
        headers={"Authorization": f"Bearer {token}"},
        json=onboarding_payload(),
    )
    assert onboarded.status_code == 201
    assert uuid.UUID(onboarded.json()["user_id"]) == existing_user_id
    assert onboarded.json()["verification_status"] == "PENDING"
    assert db_session.scalar(select(func.count()).select_from(User)) == users_before
    assert db_session.scalar(
        select(func.count()).select_from(UserNationalIdentifier).where(
            UserNationalIdentifier.user_id == existing_user_id
        )
    ) == 1


def test_onboarding_requires_auth_nid_and_rejects_duplicate_role(
    client: TestClient,
) -> None:
    assert client.post(
        "/api/v1/professionals/me/onboard", json=onboarding_payload()
    ).status_code == 401
    client.post(
        "/api/v1/auth/citizen/register",
        json=citizen_payload(
            email="bcn-only@example.com",
            nid_number=None,
            bcn="BCN-P4-ONLY",
        ),
    )
    bcn_token = login_citizen(client, "bcn-only@example.com")
    assert client.post(
        "/api/v1/professionals/me/onboard",
        headers={"Authorization": f"Bearer {bcn_token}"},
        json=onboarding_payload(),
    ).status_code == 409

    client.post(
        "/api/v1/auth/citizen/register",
        json=citizen_payload(email="duplicate-role@example.com", nid_number="ROLE-NID"),
    )
    token = login_citizen(client, "duplicate-role@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(
        "/api/v1/professionals/me/onboard",
        headers=headers,
        json=onboarding_payload(),
    ).status_code == 201
    assert client.post(
        "/api/v1/professionals/me/onboard",
        headers=headers,
        json=onboarding_payload(),
    ).status_code == 409


def test_existing_professional_can_apply_for_second_distinct_role(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/auth/citizen/register",
        json=citizen_payload(email="multi-role@example.com", nid_number="MULTI-NID"),
    )
    headers = {
        "Authorization": f"Bearer {login_citizen(client, 'multi-role@example.com')}"
    }
    first = client.post(
        "/api/v1/professionals/me/onboard",
        headers=headers,
        json=onboarding_payload(),
    )
    second = client.post(
        "/api/v1/professionals/me/onboard",
        headers=headers,
        json=onboarding_payload(role_code="NURSE"),
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["professional_id"] == second.json()["professional_id"]


def test_bmdc_number_is_globally_unique_and_conflict_rolls_back(
    client: TestClient,
    db_session,
) -> None:
    assert client.post(
        "/api/v1/auth/professional/register",
        json=professional_payload(),
    ).status_code == 201
    losing_email = "duplicate-bmdc@example.com"
    response = client.post(
        "/api/v1/auth/professional/register",
        json=professional_payload(
            email=losing_email,
            nid_number="OTHER-NID",
        ),
    )
    assert response.status_code == 409
    assert db_session.scalar(select(User).where(User.email == losing_email)) is None


def test_seeded_role_catalog_contains_exact_six_active_roles(db_session) -> None:
    roles = db_session.scalars(select(ProfessionalRole).order_by(ProfessionalRole.code)).all()
    assert {role.code for role in roles} == {
        "DOCTOR",
        "LAB_TECHNICIAN",
        "NURSE",
        "PHARMACIST",
        "RADIOLOGY_TECHNICIAN",
        "OTHER_HEALTHCARE_PROFESSIONAL",
    }
    assert all(role.is_active for role in roles)
