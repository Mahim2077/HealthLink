from collections.abc import Callable
from datetime import date, timedelta

import jwt
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.service import AuthService
from app.citizens.models import CitizenIdentifier, UserNationalIdentifier
from app.core.config import Settings
from app.core.security import REFRESH_TOKEN_COOKIE_NAME, hash_password


def registration_payload(
    *,
    email: str = "citizen@example.com",
    nid_number: str | None = "1234567890",
    birth_certificate_number: str | None = None,
) -> dict[str, object]:
    return {
        "email": email,
        "password": "StrongPassword123!",
        "first_name": "Amina",
        "last_name": "Rahman",
        "date_of_birth": "1995-05-20",
        "gender": "FEMALE",
        "blood_group": "A+",
        "address": "Dhaka",
        "nid_number": nid_number,
        "birth_certificate_number": birth_certificate_number,
    }


def register_and_login(client: TestClient) -> tuple[dict, str]:
    registration = client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(),
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "CITIZEN@example.com", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    return registration.json(), login.json()["access_token"]


def test_register_returns_account_data_without_session_cookie_or_identity_value(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(email="Citizen@Example.COM"),
    )

    assert response.status_code == 201
    assert response.json()["registered_with"] == "NID"
    assert response.json()["email"] == "citizen@example.com"
    assert "nid_number" not in response.json()
    assert "birth_certificate_number" not in response.json()
    assert "password" not in response.json()
    assert REFRESH_TOKEN_COOKIE_NAME not in response.cookies


def test_login_cookie_flags_and_refresh_token_is_not_in_json(
    client: TestClient,
) -> None:
    client.post("/api/v1/auth/citizen/register", json=registration_payload())

    response = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "citizen@example.com", "password": "StrongPassword123!"},
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "access_token",
        "token_type",
        "expires_in",
        "portal",
    }
    assert "refresh_token" not in response.json()
    set_cookie = response.headers["set-cookie"]
    assert f"{REFRESH_TOKEN_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Max-Age=" in set_cookie
    assert "Secure" not in set_cookie


def test_login_issues_citizen_session_and_self_endpoints_return_only_self_data(
    client: TestClient,
    test_settings: Settings,
) -> None:
    registration, access_token = register_and_login(client)
    authorization = {"Authorization": f"Bearer {access_token}"}

    assert REFRESH_TOKEN_COOKIE_NAME in client.cookies
    payload = jwt.decode(
        access_token,
        test_settings.jwt_secret_key,
        algorithms=[test_settings.jwt_algorithm],
    )
    assert payload["portal"] == "CITIZEN"
    assert "nid" not in payload
    assert "bcn" not in payload
    assert "nid_number" not in payload
    assert "birth_certificate_number" not in payload

    profile = client.get("/api/v1/citizens/me", headers=authorization)
    identity = client.get("/api/v1/citizens/me/identity", headers=authorization)

    assert profile.status_code == 200
    assert profile.json()["user_id"] == registration["user_id"]
    assert profile.json()["citizen_id"] == registration["citizen_id"]
    assert profile.json()["date_of_birth"] == "1995-05-20"
    assert "nid_number" not in profile.json()
    assert identity.status_code == 200
    assert identity.json() == {
        "registered_with": "NID",
        "nid_number": "1234567890",
        "birth_certificate_number": None,
        "nid_added_at": None,
    }


def test_bcn_registration_and_identity_response(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(
            email="bcn@example.com",
            nid_number=None,
            birth_certificate_number="BCN-2001-00001",
        ),
    )
    assert response.status_code == 201
    assert response.json()["registered_with"] == "BCN"

    login = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "bcn@example.com", "password": "StrongPassword123!"},
    )
    identity = client.get(
        "/api/v1/citizens/me/identity",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert identity.json()["nid_number"] is None
    assert identity.json()["birth_certificate_number"] == "BCN-2001-00001"


def test_registration_rejects_both_neither_duplicates_and_future_dob(
    client: TestClient,
) -> None:
    both = registration_payload(birth_certificate_number="BCN-BOTH")
    neither = registration_payload(nid_number=None)
    future = registration_payload(email="future@example.com", nid_number="FUTURE-NID")
    future["date_of_birth"] = str(date.today() + timedelta(days=1))

    assert client.post("/api/v1/auth/citizen/register", json=both).status_code == 422
    assert client.post("/api/v1/auth/citizen/register", json=neither).status_code == 422
    assert client.post("/api/v1/auth/citizen/register", json=future).status_code == 422

    assert (
        client.post(
            "/api/v1/auth/citizen/register",
            json=registration_payload(),
        ).status_code
        == 201
    )
    duplicate_email = registration_payload(nid_number="OTHER-NID")
    duplicate_nid = registration_payload(
        email="other@example.com",
        nid_number="1234567890",
    )
    assert (
        client.post(
            "/api/v1/auth/citizen/register",
            json=duplicate_email,
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/auth/citizen/register",
            json=duplicate_nid,
        ).status_code
        == 409
    )


def test_duplicate_bcn_returns_409_and_rolls_back_losing_account(
    client: TestClient,
    db_session,
) -> None:
    first = registration_payload(
        email="first-bcn@example.com",
        nid_number=None,
        birth_certificate_number="BCN-DUPLICATE",
    )
    losing = registration_payload(
        email="losing-bcn@example.com",
        nid_number=None,
        birth_certificate_number="BCN-DUPLICATE",
    )

    assert client.post("/api/v1/auth/citizen/register", json=first).status_code == 201
    response = client.post("/api/v1/auth/citizen/register", json=losing)

    assert response.status_code == 409
    assert db_session.scalar(
        select(User).where(User.email == "losing-bcn@example.com")
    ) is None


def test_validation_errors_redact_password_and_identity_values(
    client: TestClient,
) -> None:
    short_password = registration_payload(email="short@example.com")
    short_password["password"] = "raw"
    long_nid = registration_payload(email="nid@example.com", nid_number="N" * 33)
    long_bcn = registration_payload(
        email="bcn@example.com",
        nid_number=None,
        birth_certificate_number="B" * 65,
    )

    for payload, secret in [
        (short_password, "raw"),
        (long_nid, "N" * 33),
        (long_bcn, "B" * 65),
    ]:
        response = client.post("/api/v1/auth/citizen/register", json=payload)
        assert response.status_code == 422
        assert secret not in response.text
        assert "[REDACTED]" in response.text


def test_login_failure_is_generic_and_short_wrong_password_reaches_401(
    client: TestClient,
) -> None:
    client.post("/api/v1/auth/citizen/register", json=registration_payload())

    wrong_password = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "citizen@example.com", "password": "x"},
    )
    missing_user = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "missing@example.com", "password": "x"},
    )

    assert wrong_password.status_code == 401
    assert missing_user.status_code == 401
    assert wrong_password.json() == missing_user.json() == {
        "detail": "Invalid email or password."
    }


def test_inactive_and_profileless_users_get_generic_401_without_new_session(
    client: TestClient,
    db_session,
    user_factory: Callable[..., User],
) -> None:
    registration = client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(email="inactive@example.com"),
    )
    inactive = db_session.get(User, uuid.UUID(registration.json()["user_id"]))
    assert inactive is not None
    inactive.is_active = False

    profileless = user_factory(email="profileless@example.com")
    profileless.password_hash = hash_password("StrongPassword123!")
    db_session.commit()
    sessions_before = db_session.scalar(
        select(func.count()).select_from(AuthSession)
    )

    inactive_response = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": inactive.email, "password": "StrongPassword123!"},
    )
    profileless_response = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": profileless.email, "password": "StrongPassword123!"},
    )

    expected = {"detail": "Invalid email or password."}
    assert inactive_response.status_code == 401
    assert profileless_response.status_code == 401
    assert inactive_response.json() == expected
    assert profileless_response.json() == expected
    assert db_session.scalar(select(func.count()).select_from(AuthSession)) == (
        sessions_before
    )


def test_self_endpoints_require_citizen_portal_and_profile(
    client: TestClient,
    db_session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    assert client.get("/api/v1/citizens/me").status_code == 401

    registration, citizen_access = register_and_login(client)
    citizen_user = db_session.get(User, uuid.UUID(registration["user_id"]))
    admin_access = AuthService(db_session, test_settings).create_session(
        citizen_user.id,
        Portal.ADMIN,
    ).access_token
    assert (
        client.get(
            "/api/v1/citizens/me",
            headers={"Authorization": f"Bearer {admin_access}"},
        ).status_code
        == 403
    )

    base_user = user_factory()
    citizen_without_profile = AuthService(db_session, test_settings).create_session(
        base_user.id,
        Portal.CITIZEN,
    ).access_token
    assert (
        client.get(
            "/api/v1/citizens/me",
            headers={"Authorization": f"Bearer {citizen_without_profile}"},
        ).status_code
        == 403
    )


def test_each_citizen_token_reads_only_its_own_profile(client: TestClient) -> None:
    first_registration, first_access = register_and_login(client)
    second_registration = client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(email="second@example.com", nid_number="SECOND-NID"),
    ).json()
    second_access = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "second@example.com", "password": "StrongPassword123!"},
    ).json()["access_token"]

    first_profile = client.get(
        "/api/v1/citizens/me",
        headers={"Authorization": f"Bearer {first_access}"},
    ).json()
    second_profile = client.get(
        "/api/v1/citizens/me",
        headers={"Authorization": f"Bearer {second_access}"},
    ).json()

    assert first_profile["user_id"] == first_registration["user_id"]
    assert second_profile["user_id"] == second_registration["user_id"]
    assert first_profile["user_id"] != second_profile["user_id"]


def test_citizen_can_update_only_their_editable_profile_fields(
    client: TestClient,
    db_session,
) -> None:
    registration, access_token = register_and_login(client)
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.put(
        "/api/v1/citizens/me/profile",
        headers=headers,
        json={
            "first_name": "  Ayesha  ",
            "last_name": "  Karim  ",
            "date_of_birth": "1994-04-14",
            "gender": "FEMALE",
            "blood_group": "B+",
            "address": "Chattogram",
        },
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Ayesha"
    assert response.json()["last_name"] == "Karim"
    assert response.json()["date_of_birth"] == "1994-04-14"
    assert response.json()["address"] == "Chattogram"
    user = db_session.get(User, uuid.UUID(registration["user_id"]))
    assert user is not None
    assert (user.first_name, user.last_name) == ("Ayesha", "Karim")

    forbidden = client.put(
        "/api/v1/citizens/me/profile",
        headers=headers,
        json={
            "first_name": "Ayesha",
            "last_name": "Karim",
            "date_of_birth": "1994-04-14",
            "gender": "FEMALE",
            "blood_group": "B+",
            "address": "Chattogram",
            "nid_number": "MUST-NOT-BE-ACCEPTED",
        },
    )
    assert forbidden.status_code == 422
    identity = client.get("/api/v1/citizens/me/identity", headers=headers)
    assert identity.json()["nid_number"] == "1234567890"


def test_profile_update_requires_citizen_portal_and_never_updates_another_user(
    client: TestClient,
    db_session,
    test_settings: Settings,
) -> None:
    first_registration, first_access = register_and_login(client)
    second_registration = client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(email="second-profile@example.com", nid_number="PROFILE-2"),
    ).json()
    second_user = db_session.get(User, uuid.UUID(second_registration["user_id"]))
    assert second_user is not None

    admin_access = AuthService(db_session, test_settings).create_session(
        uuid.UUID(first_registration["user_id"]),
        Portal.ADMIN,
    ).access_token
    payload = {
        "first_name": "Only",
        "last_name": "Mine",
        "date_of_birth": "1990-01-01",
        "gender": "OTHER",
        "blood_group": None,
        "address": None,
    }
    assert client.put("/api/v1/citizens/me/profile", json=payload).status_code == 401
    assert client.put(
        "/api/v1/citizens/me/profile",
        headers={"Authorization": f"Bearer {admin_access}"},
        json=payload,
    ).status_code == 403
    assert client.put(
        "/api/v1/citizens/me/profile",
        headers={"Authorization": f"Bearer {first_access}"},
        json=payload,
    ).status_code == 200
    db_session.refresh(second_user)
    assert (second_user.first_name, second_user.last_name) == ("Amina", "Rahman")


def test_bcn_citizen_adds_nid_once_and_retains_birth_certificate(
    client: TestClient,
    db_session,
) -> None:
    registration = client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(
            email="upgrade@example.com",
            nid_number=None,
            birth_certificate_number="BCN-UPGRADE-001",
        ),
    ).json()
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "upgrade@example.com", "password": "StrongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post(
        "/api/v1/citizens/me/identity/add-nid",
        headers=headers,
        json={"nid_number": "  NID-UPGRADE-001  ", "confirmation": "CONFIRM"},
    )

    assert response.status_code == 200
    assert response.json()["registered_with"] == "BCN"
    assert response.json()["nid_number"] == "NID-UPGRADE-001"
    assert response.json()["birth_certificate_number"] == "BCN-UPGRADE-001"
    assert response.json()["nid_added_at"] is not None
    identity = db_session.scalar(
        select(CitizenIdentifier).where(
            CitizenIdentifier.user_id == uuid.UUID(registration["user_id"])
        )
    )
    assert identity is not None
    assert identity.birth_certificate_number == "BCN-UPGRADE-001"
    assert identity.national_identifier_id is not None
    assert identity.nid_added_at is not None
    national_identifier = db_session.get(
        UserNationalIdentifier,
        identity.national_identifier_id,
    )
    assert national_identifier is not None
    assert national_identifier.nid_number == "NID-UPGRADE-001"

    second = client.post(
        "/api/v1/citizens/me/identity/add-nid",
        headers=headers,
        json={"nid_number": "REPLACEMENT-NID", "confirmation": "CONFIRM"},
    )
    assert second.status_code == 409
    db_session.refresh(identity)
    assert identity.national_identifier_id == national_identifier.id


def test_add_nid_requires_exact_confirmation_and_global_unique_value(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(email="existing-nid@example.com"),
    )
    client.post(
        "/api/v1/auth/citizen/register",
        json=registration_payload(
            email="new-bcn@example.com",
            nid_number=None,
            birth_certificate_number="BCN-NEW-001",
        ),
    )
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={"email": "new-bcn@example.com", "password": "StrongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    for confirmation in ["confirm", " CONFIRM", "CONFIRM "]:
        response = client.post(
            "/api/v1/citizens/me/identity/add-nid",
            headers=headers,
            json={"nid_number": "NEW-UNUSED-NID", "confirmation": confirmation},
        )
        assert response.status_code == 400

    duplicate = client.post(
        "/api/v1/citizens/me/identity/add-nid",
        headers=headers,
        json={"nid_number": "1234567890", "confirmation": "CONFIRM"},
    )
    assert duplicate.status_code == 409
    identity = client.get("/api/v1/citizens/me/identity", headers=headers)
    assert identity.json()["nid_number"] is None
    assert identity.json()["birth_certificate_number"] == "BCN-NEW-001"


def test_add_nid_rejects_initial_nid_citizen_and_wrong_portal(
    client: TestClient,
    db_session,
    test_settings: Settings,
) -> None:
    registration, access_token = register_and_login(client)
    payload = {"nid_number": "ANOTHER-NID", "confirmation": "CONFIRM"}
    response = client.post(
        "/api/v1/citizens/me/identity/add-nid",
        headers={"Authorization": f"Bearer {access_token}"},
        json=payload,
    )
    assert response.status_code == 409

    admin_access = AuthService(db_session, test_settings).create_session(
        uuid.UUID(registration["user_id"]),
        Portal.ADMIN,
    ).access_token
    assert client.post(
        "/api/v1/citizens/me/identity/add-nid",
        headers={"Authorization": f"Bearer {admin_access}"},
        json=payload,
    ).status_code == 403
