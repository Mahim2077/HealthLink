from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.admins.models import AdminAccount, AdminActionLog
from app.admins.provisioning import create_trusted_admin
from app.facilities.models import HealthcareFacility
from app.professionals.models import ProfessionalRoleRegistration


ADMIN_PASSWORD = "StrongAdminPassword123!"


def admin_headers(client: TestClient, db_session) -> tuple[dict[str, str], uuid.UUID]:
    provisioned = create_trusted_admin(
        db_session,
        email=f"admin-{uuid.uuid4().hex}@example.com",
        password=ADMIN_PASSWORD,
        first_name="Review",
        last_name="Admin",
        is_super_admin=False,
    )
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": provisioned.user.email, "password": ADMIN_PASSWORD},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, provisioned.user.id


def register_professional(
    client: TestClient, *, role_code: str = "DOCTOR", suffix: str | None = None
) -> dict:
    unique = suffix or uuid.uuid4().hex[:20]
    payload = {
        "email": f"professional-{unique}@example.com",
        "password": "StrongPassword123!",
        "first_name": "Pending",
        "last_name": "Professional",
        "nid_number": f"NID-{unique}",
        "role_code": role_code,
        "facility_name": "Submitted Medical Centre",
        "designation": "Consultant" if role_code == "DOCTOR" else "Technician",
        "additional_info": "Role-specific supporting information.",
    }
    if role_code == "DOCTOR":
        payload["bmdc_registration_number"] = f"BMDC-{unique}"
    response = client.post("/api/v1/auth/professional/register", json=payload)
    assert response.status_code == 201, response.text
    return {**response.json(), "bmdc": payload.get("bmdc_registration_number")}


def facility_payload(**overrides) -> dict:
    payload = {
        "name": "HealthLink General Hospital",
        "facility_type": "HOSPITAL",
        "registration_number": "FAC-001",
        "address": "12 Care Road, Dhaka",
        "phone": "+8801700000000",
        "email": "facility@example.com",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_facility_crud_requires_admin_and_writes_audit(
    client: TestClient, db_session
) -> None:
    headers, admin_user_id = admin_headers(client, db_session)
    assert client.get("/api/v1/admin/facilities").status_code == 401

    created = client.post(
        "/api/v1/admin/facilities",
        headers=headers,
        json=facility_payload(name="  HealthLink General Hospital  "),
    )
    assert created.status_code == 201
    facility = created.json()
    assert facility["name"] == "HealthLink General Hospital"
    assert facility["facility_type"] == "HOSPITAL"

    listed = client.get("/api/v1/admin/facilities", headers=headers)
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [facility["id"]]

    updated = client.put(
        f"/api/v1/admin/facilities/{facility['id']}",
        headers=headers,
        json=facility_payload(
            name="HealthLink City Clinic", facility_type="CLINIC", is_active=False
        ),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "HealthLink City Clinic"
    assert updated.json()["is_active"] is False

    actions = list(
        db_session.scalars(
            select(AdminActionLog)
            .where(AdminActionLog.admin_user_id == admin_user_id)
            .order_by(AdminActionLog.created_at)
        )
    )
    assert [action.action_type for action in actions] == [
        "FACILITY_CREATE",
        "FACILITY_UPDATE",
    ]
    assert all(
        action.target_resource_id == uuid.UUID(facility["id"]) for action in actions
    )
    admin = db_session.scalar(
        select(AdminAccount).where(AdminAccount.user_id == admin_user_id)
    )
    assert admin is not None
    admin.is_active = False
    db_session.commit()
    assert client.get("/api/v1/admin/facilities", headers=headers).status_code == 403


def test_queue_detail_exposes_doctor_bmdc_and_can_verify_with_facility(
    client: TestClient, db_session
) -> None:
    headers, admin_user_id = admin_headers(client, db_session)
    application = register_professional(client)
    facility = client.post(
        "/api/v1/admin/facilities", headers=headers, json=facility_payload()
    ).json()

    queue = client.get(
        "/api/v1/admin/professional-registrations?verification_status=PENDING",
        headers=headers,
    )
    assert queue.status_code == 200
    assert any(
        row["id"] == application["role_registration_id"] for row in queue.json()
    )

    detail = client.get(
        f"/api/v1/admin/professional-registrations/{application['role_registration_id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["role_code"] == "DOCTOR"
    assert detail.json()["bmdc_registration_number"] == application["bmdc"]
    assert detail.json()["facility"] is None

    verified = client.post(
        f"/api/v1/admin/professional-registrations/{application['role_registration_id']}/verify",
        headers=headers,
        json={"facility_id": facility["id"]},
    )
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["verification_status"] == "VERIFIED"
    assert body["facility"]["id"] == facility["id"]
    assert body["verified_by"] == str(admin_user_id)
    assert body["verified_at"] is not None
    assert body["rejected_at"] is None

    retry = client.post(
        f"/api/v1/admin/professional-registrations/{application['role_registration_id']}/verify",
        headers=headers,
        json={"facility_id": facility["id"]},
    )
    assert retry.status_code == 409

    audit = db_session.scalar(
        select(AdminActionLog).where(
            AdminActionLog.action_type == "PROFESSIONAL_VERIFY",
            AdminActionLog.target_resource_id
            == uuid.UUID(application["role_registration_id"]),
        )
    )
    assert audit is not None
    assert audit.admin_user_id == admin_user_id
    assert audit.target_user_id == uuid.UUID(application["user_id"])
    assert audit.reason is None


def test_rejection_requires_reason_is_audited_and_cannot_be_redecided(
    client: TestClient, db_session
) -> None:
    headers, admin_user_id = admin_headers(client, db_session)
    application = register_professional(client, role_code="LAB_TECHNICIAN")
    endpoint = (
        f"/api/v1/admin/professional-registrations/"
        f"{application['role_registration_id']}/reject"
    )
    for reason in ["", "   "]:
        response = client.post(endpoint, headers=headers, json={"reason": reason})
        assert response.status_code == 422

    rejected = client.post(
        endpoint,
        headers=headers,
        json={"reason": "  Submitted evidence could not be validated.  "},
    )
    assert rejected.status_code == 200
    assert rejected.json()["verification_status"] == "REJECTED"
    assert rejected.json()["rejection_reason"] == "Submitted evidence could not be validated."
    assert rejected.json()["rejected_at"] is not None
    assert rejected.json()["facility"] is None
    assert client.post(
        endpoint, headers=headers, json={"reason": "Second decision"}
    ).status_code == 409

    audit = db_session.scalar(
        select(AdminActionLog).where(
            AdminActionLog.action_type == "PROFESSIONAL_REJECT"
        )
    )
    assert audit is not None
    assert audit.admin_user_id == admin_user_id
    assert audit.reason == "Submitted evidence could not be validated."


def test_verification_rejects_missing_or_inactive_facility_without_mutation(
    client: TestClient, db_session
) -> None:
    headers, _ = admin_headers(client, db_session)
    application = register_professional(client)
    inactive = HealthcareFacility(**facility_payload(is_active=False))
    db_session.add(inactive)
    db_session.commit()
    endpoint = (
        f"/api/v1/admin/professional-registrations/"
        f"{application['role_registration_id']}/verify"
    )
    for facility_id in [uuid.uuid4(), inactive.id]:
        response = client.post(
            endpoint, headers=headers, json={"facility_id": str(facility_id)}
        )
        assert response.status_code == 409
    registration = db_session.get(
        ProfessionalRoleRegistration, uuid.UUID(application["role_registration_id"])
    )
    db_session.refresh(registration)
    assert registration.verification_status == "PENDING"
    assert registration.facility_id is None
