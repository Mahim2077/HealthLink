from collections.abc import Callable
from pathlib import Path
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.admins.models import AdminAccount, AdminActionLog
from app.admins.provisioning import AdminProvisioningError, create_trusted_admin
from app.admins.service import _DUMMY_ADMIN_PASSWORD_HASH
from app.auth.models import AuthSession, User
from app.core.config import Settings
from app.core.security import REFRESH_TOKEN_COOKIE_NAME, verify_password


def provision_admin(db_session, *, email: str = "admin@example.com", super_admin: bool = True):
    return create_trusted_admin(
        db_session,
        email=email,
        password="StrongAdminPassword123!",
        first_name="Trusted",
        last_name="Administrator",
        is_super_admin=super_admin,
    )


def test_trusted_provisioning_creates_hashed_admin_without_audit_side_effect(db_session) -> None:
    provisioned = provision_admin(db_session, email=" Admin@Example.COM ")
    assert provisioned.user.email == "admin@example.com"
    assert provisioned.user.password_hash != "StrongAdminPassword123!"
    assert verify_password("StrongAdminPassword123!", provisioned.user.password_hash)
    assert provisioned.admin.is_active
    assert provisioned.admin.is_super_admin
    assert db_session.scalar(select(func.count()).select_from(AdminActionLog)) == 0
    with pytest.raises(AdminProvisioningError):
        provision_admin(db_session, email="admin@example.com")


def test_admin_login_issues_admin_session_cookie_and_me_response(
    client: TestClient,
    db_session,
    test_settings: Settings,
) -> None:
    provisioned = provision_admin(db_session)
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": " ADMIN@example.com ", "password": "StrongAdminPassword123!"},
    )
    assert response.status_code == 200
    assert response.json()["portal"] == "ADMIN"
    assert "refresh_token" not in response.json()
    assert REFRESH_TOKEN_COOKIE_NAME in response.cookies
    claims = jwt.decode(
        response.json()["access_token"],
        test_settings.jwt_secret_key,
        algorithms=[test_settings.jwt_algorithm],
    )
    assert claims["portal"] == "ADMIN"
    me = client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json() == {
        "user_id": str(provisioned.user.id),
        "admin_id": str(provisioned.admin.id),
        "email": "admin@example.com",
        "first_name": "Trusted",
        "last_name": "Administrator",
        "is_super_admin": True,
    }


def test_unknown_normal_user_inactive_user_and_inactive_admin_share_generic_401(
    client: TestClient,
    db_session,
    user_factory: Callable[..., User],
) -> None:
    provisioned = provision_admin(db_session)
    normal = user_factory(email="normal@example.com")
    from app.core.security import hash_password

    normal.password_hash = hash_password("StrongAdminPassword123!")
    inactive_user_admin = provision_admin(db_session, email="inactive-user@example.com")
    inactive_user_admin.user.is_active = False
    inactive_admin = provision_admin(db_session, email="inactive-admin@example.com")
    inactive_admin.admin.is_active = False
    db_session.commit()
    sessions_before = db_session.scalar(select(func.count()).select_from(AuthSession))

    attempts = [
        ("missing@example.com", "wrong"),
        ("admin@example.com", "wrong"),
        (normal.email, "StrongAdminPassword123!"),
        (inactive_user_admin.user.email, "StrongAdminPassword123!"),
        (inactive_admin.user.email, "StrongAdminPassword123!"),
    ]
    for email, password in attempts:
        response = client.post(
            "/api/v1/auth/admin/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password."}
    assert db_session.scalar(select(func.count()).select_from(AuthSession)) == sessions_before


def test_admin_login_always_verifies_one_valid_hash(
    client: TestClient,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioned = provision_admin(db_session)
    hashes: list[str] = []

    def record(_password: str, password_hash: str) -> bool:
        hashes.append(password_hash)
        return False

    monkeypatch.setattr("app.admins.service.verify_password", record)
    for email in ["missing@example.com", provisioned.user.email]:
        assert client.post(
            "/api/v1/auth/admin/login",
            json={"email": email, "password": "wrong"},
        ).status_code == 401
    assert hashes == [_DUMMY_ADMIN_PASSWORD_HASH, provisioned.user.password_hash]
    assert verify_password("HealthLink-login-dummy-password", _DUMMY_ADMIN_PASSWORD_HASH)


def test_admin_me_enforces_portal_and_current_admin_activity(
    client: TestClient,
    db_session,
) -> None:
    provisioned = provision_admin(db_session)
    login = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "admin@example.com", "password": "StrongAdminPassword123!"},
    )
    token = login.json()["access_token"]
    assert client.get("/api/v1/admin/me").status_code == 401

    client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": "citizen@example.com",
            "password": "StrongPassword123!",
            "first_name": "Citizen",
            "last_name": "User",
            "date_of_birth": "1990-01-01",
            "gender": "OTHER",
            "nid_number": "ADMIN-WRONG-PORTAL-NID",
        },
    )
    citizen_login = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "citizen@example.com", "password": "StrongPassword123!"},
    )
    assert client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {citizen_login.json()['access_token']}"},
    ).status_code == 403

    provisioned.admin.is_active = False
    db_session.commit()
    assert client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 403


def test_no_public_admin_registration_route_and_script_has_no_password_argument(
    client: TestClient,
) -> None:
    assert client.post("/api/v1/auth/admin/register", json={}).status_code == 404
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "create_admin.py"
    ).read_text(encoding="utf-8")
    assert 'add_argument("--password"' not in script
    assert "getpass(" in script
