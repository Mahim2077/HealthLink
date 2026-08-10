from __future__ import annotations

from collections.abc import Callable
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.admins.models import AdminActionLog
from app.admins.provisioning import create_trusted_admin
from app.auth.constants import Portal
from app.auth.models import User
from app.auth.service import AuthService
from app.citizens.constants import CitizenRegistrationMethod
from app.citizens.models import CitizenIdentifier, UserNationalIdentifier
from app.core.config import Settings


ADMIN_PASSWORD = "StrongAdminPassword123!"
CITIZEN_PASSWORD = "StrongPassword123!"


def _provision_admin(db_session, *, email: str = "admin@example.com") -> object:
    return create_trusted_admin(
        db_session,
        email=email,
        password=ADMIN_PASSWORD,
        first_name="Trusted",
        last_name="Admin",
        is_super_admin=True,
    )


def _admin_user_id(db_session) -> uuid.UUID:
    return db_session.scalar(select(User).where(User.email == "admin@example.com")).id


def _register_citizen(
    client: TestClient,
    *,
    email: str = "citizen@example.com",
    nid_number: str | None = "NID-INIT-0001",
    birth_certificate_number: str | None = None,
) -> dict:
    payload = {
        "email": email,
        "password": CITIZEN_PASSWORD,
        "first_name": "Amina",
        "last_name": "Rahman",
        "date_of_birth": "1995-05-20",
        "gender": "FEMALE",
        "blood_group": "A+",
        "address": "Dhaka",
        "nid_number": nid_number,
        "birth_certificate_number": birth_certificate_number,
    }
    response = client.post("/api/v1/auth/citizen/register", json=payload)
    assert response.status_code == 201
    return response.json()


def _admin_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@example.com", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _citizen_token(
    client: TestClient, *, email: str = "citizen@example.com"
) -> str:
    response = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": email, "password": CITIZEN_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_search_requires_no_filter_returns_400_and_writes_no_audit(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    token = _admin_token(client)
    before = db_session.scalar(select(func.count()).select_from(AdminActionLog))

    response = client.get(
        "/api/v1/admin/citizen-identities/search",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "Provide at least one" in response.json()["detail"]
    assert db_session.scalar(select(func.count()).select_from(AdminActionLog)) == before


def test_search_requires_admin_authentication(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    _register_citizen(client)
    citizen = _citizen_token(client)

    response = client.get(
        "/api/v1/admin/citizen-identities/search?nid_number=NID-INIT-0001",
        headers={"Authorization": f"Bearer {citizen}"},
    )

    assert response.status_code == 403


def test_search_requires_authenticated_session(client: TestClient) -> None:
    response = client.get(
        "/api/v1/admin/citizen-identities/search?nid_number=NID-INIT-0001",
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Search across each filter
# ---------------------------------------------------------------------------


def test_search_finds_citizen_by_each_filter(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    _register_citizen(client)
    _register_citizen(
        client,
        email="minor@example.com",
        nid_number=None,
        birth_certificate_number="BCN-INIT-0001",
    )
    token = _admin_token(client)

    by_nid = client.get(
        "/api/v1/admin/citizen-identities/search?nid_number=NID-INIT-0001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert by_nid.status_code == 200
    body = by_nid.json()
    assert len(body) == 1
    assert body[0]["email"] == "citizen@example.com"
    assert body[0]["nid_number"] == "NID-INIT-0001"
    assert body[0]["registered_with"] == "NID"

    by_bcn = client.get(
        "/api/v1/admin/citizen-identities/search"
        "?birth_certificate_number=BCN-INIT-0001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert by_bcn.status_code == 200
    assert len(by_bcn.json()) == 1
    assert by_bcn.json()[0]["registered_with"] == "BCN"

    by_email = client.get(
        "/api/v1/admin/citizen-identities/search?email=citizen@example.com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert by_email.status_code == 200
    assert [row["email"] for row in by_email.json()] == ["citizen@example.com"]


def test_search_strips_whitespace_filters(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    _register_citizen(client)
    token = _admin_token(client)

    response = client.get(
        "/api/v1/admin/citizen-identities/search?nid_number=%20NID-INIT-0001%20",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_limit_is_clamped_by_schema(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    token = _admin_token(client)

    over = client.get(
        "/api/v1/admin/citizen-identities/search?limit=999",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Pydantic surfaces the le=50 violation as a 422 ValidationError rather than a
    # service-defined 400 — the schema-level clamp is what we actually care about.
    assert over.status_code == 422
    body = over.json()
    assert any("limit" in err["loc"] for err in body.get("detail", []))


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


def test_detail_returns_user_identity_profile_and_session_count(
    client: TestClient, db_session, test_settings: Settings
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(client)
    token = _admin_token(client)
    # Create an auth session for the citizen so the count is observable.
    AuthService(db_session, test_settings).create_session(
        uuid.UUID(registered["user_id"]), Portal.CITIZEN
    )

    response = client.get(
        f"/api/v1/admin/citizen-identities/{registered['user_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == registered["user_id"]
    assert body["email"] == "citizen@example.com"
    assert body["registered_with"] == "NID"
    assert body["nid_number"] == "NID-INIT-0001"
    assert body["birth_certificate_number"] is None
    assert body["national_identifier_id"]
    assert body["date_of_birth"] == "1995-05-20"
    assert body["gender"] == "FEMALE"
    assert body["blood_group"] == "A+"
    assert body["address"] == "Dhaka"
    assert body["auth_session_count"] == 1


def test_detail_returns_404_for_unknown_user(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    token = _admin_token(client)

    response = client.get(
        f"/api/v1/admin/citizen-identities/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Citizen not found."


# ---------------------------------------------------------------------------
# NID correction
# ---------------------------------------------------------------------------


def test_correct_nid_replaces_existing_number_and_writes_audit(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(client)
    token = _admin_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{registered['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "NID",
            "new_value": "NID-CORRECTED-0001",
            "reason": "Original NID had a transcription error.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correction_type"] == "NID"
    assert body["previous_value"] == "NID-INIT-0001"
    assert body["new_value"] == "NID-CORRECTED-0001"
    assert body["audit_log_id"]

    nid_row = db_session.scalar(
        select(UserNationalIdentifier).where(
            UserNationalIdentifier.user_id == uuid.UUID(registered["user_id"])
        )
    )
    assert nid_row is not None
    assert nid_row.nid_number == "NID-CORRECTED-0001"

    audit = db_session.get(AdminActionLog, uuid.UUID(body["audit_log_id"]))
    assert audit is not None
    assert audit.admin_user_id == _admin_user_id(db_session)
    assert audit.action_type == "CITIZEN_IDENTITY_CORRECT_NID"
    assert audit.target_user_id == uuid.UUID(registered["user_id"])
    assert audit.target_resource_type == "USER_NATIONAL_IDENTIFIER"
    assert audit.reason == "Original NID had a transcription error."


def test_correct_nid_adds_first_nid_for_bcn_citizen(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(
        client,
        email="minor@example.com",
        nid_number=None,
        birth_certificate_number="BCN-INIT-0002",
    )
    token = _admin_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{registered['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "NID",
            "new_value": "NID-ADDED-0001",
            "reason": "Citizen supplied missing NID via support.",
        },
    )

    assert response.status_code == 200
    assert response.json()["previous_value"] is None
    identity = db_session.scalar(
        select(CitizenIdentifier).where(
            CitizenIdentifier.user_id == uuid.UUID(registered["user_id"])
        )
    )
    assert identity is not None
    assert identity.national_identifier_id is not None
    assert identity.birth_certificate_number == "BCN-INIT-0002"


def test_correct_nid_rejects_conflict_with_other_citizen(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    primary = _register_citizen(client)
    _register_citizen(
        client,
        email="other@example.com",
        nid_number="NID-OTHER-0001",
        birth_certificate_number=None,
    )
    token = _admin_token(client)
    before = db_session.scalar(select(func.count()).select_from(AdminActionLog))

    response = client.post(
        f"/api/v1/admin/citizen-identities/{primary['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "NID",
            "new_value": "NID-OTHER-0001",
            "reason": "Trying to grab someone else's NID.",
        },
    )

    assert response.status_code == 409
    assert "another citizen" in response.json()["detail"].lower()
    assert (
        db_session.scalar(select(func.count()).select_from(AdminActionLog))
        == before
    )

    other_user = db_session.scalar(
        select(User).where(User.email == "other@example.com")
    )
    assert other_user is not None
    other = db_session.scalar(
        select(UserNationalIdentifier).where(
            UserNationalIdentifier.nid_number == "NID-OTHER-0001"
        )
    )
    assert other is not None
    assert other.user_id == other_user.id


# ---------------------------------------------------------------------------
# BCN correction
# ---------------------------------------------------------------------------


def test_correct_bcn_replaces_existing_number_and_writes_audit(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(
        client,
        email="minor@example.com",
        nid_number=None,
        birth_certificate_number="BCN-INIT-0003",
    )
    token = _admin_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{registered['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "BCN",
            "new_value": "BCN-CORRECTED-0003",
            "reason": "Clerical correction per registrar record.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correction_type"] == "BCN"
    assert body["previous_value"] == "BCN-INIT-0003"
    assert body["new_value"] == "BCN-CORRECTED-0003"

    identity = db_session.scalar(
        select(CitizenIdentifier).where(
            CitizenIdentifier.user_id == uuid.UUID(registered["user_id"])
        )
    )
    assert identity is not None
    assert identity.birth_certificate_number == "BCN-CORRECTED-0003"

    audit = db_session.get(AdminActionLog, uuid.UUID(body["audit_log_id"]))
    assert audit is not None
    assert audit.action_type == "CITIZEN_IDENTITY_CORRECT_BCN"
    assert audit.target_resource_type == "CITIZEN_BIRTH_CERTIFICATE"


def test_correct_bcn_rejects_conflict_with_other_citizen(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    primary = _register_citizen(
        client,
        email="primary@example.com",
        nid_number=None,
        birth_certificate_number="BCN-A-0001",
    )
    _register_citizen(
        client,
        email="secondary@example.com",
        nid_number=None,
        birth_certificate_number="BCN-B-0001",
    )
    token = _admin_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{primary['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "BCN",
            "new_value": "BCN-B-0001",
            "reason": "Should fail conflict.",
        },
    )

    assert response.status_code == 409


def test_correct_bcn_on_nid_only_citizen_returns_state_error(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(client, nid_number="NID-ONLY-0001")
    token = _admin_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{registered['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "BCN",
            "new_value": "BCN-DOES-NOT-APPLY",
            "reason": "No BCN exists.",
        },
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Reason + validation
# ---------------------------------------------------------------------------


def test_correct_requires_non_blank_reason(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(client)
    token = _admin_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{registered['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "NID",
            "new_value": "NID-WHATEVER",
            "reason": "   ",
        },
    )

    assert response.status_code == 422


def test_correct_rejects_unknown_user(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    token = _admin_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{uuid.uuid4()}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "NID",
            "new_value": "NID-ANY",
            "reason": "Whatever",
        },
    )

    assert response.status_code == 404


def test_correct_rejects_non_admin_caller(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(client)
    citizen = _citizen_token(client)

    response = client.post(
        f"/api/v1/admin/citizen-identities/{registered['user_id']}/correct",
        headers={"Authorization": f"Bearer {citizen}"},
        json={
            "correction_type": "NID",
            "new_value": "NID-NONADMIN",
            "reason": "Trying without admin rights.",
        },
    )

    assert response.status_code == 403


def test_correct_does_not_merge_accounts_when_target_user_id_is_other_citizen(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    primary = _register_citizen(client)
    other = _register_citizen(
        client,
        email="sibling@example.com",
        nid_number="NID-SIBLING-0001",
    )
    token = _admin_token(client)

    # Try to overwrite the sibling's NID using the primary user's correction
    # endpoint. The unique constraint must reject this without any merge.
    response = client.post(
        f"/api/v1/admin/citizen-identities/{primary['user_id']}/correct",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "correction_type": "NID",
            "new_value": "NID-SIBLING-0001",
            "reason": "Trying to claim sibling NID.",
        },
    )

    assert response.status_code == 409

    sibling = db_session.scalar(
        select(UserNationalIdentifier).where(
            UserNationalIdentifier.nid_number == "NID-SIBLING-0001"
        )
    )
    assert sibling is not None
    assert sibling.user_id == uuid.UUID(other["user_id"])
    primary_user = db_session.get(User, uuid.UUID(primary["user_id"]))
    assert primary_user is not None
    assert primary_user.email == "citizen@example.com"


# ---------------------------------------------------------------------------
# Search by user_id
# ---------------------------------------------------------------------------


def test_search_by_user_id_returns_citizen(
    client: TestClient, db_session
) -> None:
    _provision_admin(db_session)
    registered = _register_citizen(client)
    token = _admin_token(client)

    response = client.get(
        f"/api/v1/admin/citizen-identities/search?user_id={registered['user_id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == registered["user_id"]