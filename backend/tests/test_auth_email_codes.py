import os
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.admins.provisioning import create_trusted_admin
from app.auth import email_code_routes, email_codes
from app.auth.models import EmailCodeChallenge, User
from app.core.security import REFRESH_TOKEN_COOKIE_NAME
from app.db.session import create_database_engine
from test_citizen_routes import registration_payload
from test_professional_routes import professional_payload


BASE = "/api/v1/auth"


@pytest.fixture(params=["sqlite", "postgresql"])
def db_session(db_session, request):
    if request.param == "sqlite":
        yield db_session
        return
    url = os.getenv("HEALTHLINK_TEST_DATABASE_URL")
    if not url:
        pytest.skip("HEALTHLINK_TEST_DATABASE_URL is required for PostgreSQL coverage")
    engine = create_database_engine(url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:
            with Session(connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
                yield session
            transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def mailbox(client, monkeypatch):
    settings = client.app.state.settings
    settings.auth_email_otp_enabled = True
    settings.auth_email_otp_secret = "test-only-email-otp-secret-with-32-bytes"
    messages = []

    def deliver(_settings, recipient, subject, body):
        messages.append((recipient, subject, body))

    monkeypatch.setattr(email_code_routes, "send_auth_email", deliver)
    monkeypatch.setattr(email_code_routes, "send_auth_email_in_background", deliver)
    return messages


def _code(mailbox):
    return re.search(r"\b[0-9]{6}\b", mailbox[-1][2]).group()


def _headers(response):
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.mark.parametrize("portal", ["CITIZEN", "PROFESSIONAL"])
def test_signup_requires_email_proof_and_preserves_portal_rules(client, db_session, mailbox, portal):
    url = f"{BASE}/{portal.lower()}/register"
    payload = registration_payload() if portal == "CITIZEN" else professional_payload()
    assert client.post(url, json=payload).status_code == 428
    request = client.post(f"{BASE}/email/signup", json={"email": payload["email"], "portal": portal})
    assert request.status_code == 202
    proof = {"challenge_id": request.json()["challenge_id"], "code": _code(mailbox)}
    assert set(request.json()) == {"challenge_id", "resend_after_seconds"}
    assert client.post(f"{BASE}/email/reset/verify", json=proof).status_code == 400
    assert client.post(url, json={**payload, **proof, "email": "other@example.com"}).status_code == 400
    wrong = "000000" if proof["code"] != "000000" else "111111"
    assert client.post(url, json={**payload, **proof, "code": wrong}).status_code == 400
    result = client.post(url, json={**payload, **proof})
    assert result.status_code == 201, result.text
    assert result.json()["portal"] == portal
    assert "HttpOnly" in result.headers["set-cookie"]
    assert client.post(f"{BASE}/refresh").json()["portal"] == portal
    if portal == "PROFESSIONAL":
        assert result.json()["verification_status"] == "PENDING"
    assert db_session.get(User, uuid.UUID(result.json()["user_id"])).email_verified_at is not None
    assert db_session.get(EmailCodeChallenge, uuid.UUID(proof["challenge_id"])) is None
    assert client.post(url, json={**payload, **proof}).status_code == 409


def test_legacy_email_enrollment_and_reset_revoke_existing_sessions(client, mailbox, monkeypatch):
    settings = client.app.state.settings
    settings.auth_email_otp_enabled = False
    payload = registration_payload()
    payload["password"] = "weakpass"
    assert client.post(f"{BASE}/citizen/register", json=payload).status_code == 201
    settings.auth_email_otp_enabled = True
    sign_in = {"email": payload["email"], "password": payload["password"]}
    login = client.post(f"{BASE}/citizen/login", json=sign_in)
    headers = _headers(login)
    refresh_cookie = login.cookies[REFRESH_TOKEN_COOKIE_NAME]
    reset = {"portal": "CITIZEN", "email": payload["email"]}
    before = client.post(f"{BASE}/email/reset", json=reset)
    unknown = client.post(f"{BASE}/email/reset", json={**reset, "email": "unknown@example.com"})
    assert before.status_code == unknown.status_code == 202
    assert before.json().keys() == unknown.json().keys()
    assert not mailbox
    assert client.get(f"{BASE}/email/status", headers=headers).json()["verified"] is False
    assert client.post(f"{BASE}/email/enroll", json={"password": "wrong"}, headers=headers).status_code == 400
    enroll = client.post(f"{BASE}/email/enroll", json={"password": payload["password"]}, headers=headers)
    assert enroll.status_code == 202
    proof = {"challenge_id": enroll.json()["challenge_id"], "code": _code(mailbox)}
    assert client.post(f"{BASE}/email/enroll/verify", json=proof).status_code == 401
    assert client.post(f"{BASE}/email/enroll/verify", json=proof, headers=headers).status_code == 204
    assert client.get(f"{BASE}/email/status", headers=headers).json()["verified"] is True
    now = email_codes.utc_now() + timedelta(seconds=61)
    monkeypatch.setattr(email_codes, "utc_now", lambda: now)
    request = client.post(f"{BASE}/email/reset", json=reset)
    proof = {"challenge_id": request.json()["challenge_id"], "code": _code(mailbox)}
    assert mailbox[-1][1] == "Reset your HealthLink password"
    verified = client.post(f"{BASE}/email/reset/verify", json=proof)
    assert verified.status_code == 200
    assert client.post(f"{BASE}/email/reset/verify", json=proof).status_code == 400
    completion = {
        "challenge_id": proof["challenge_id"],
        "reset_token": verified.json()["reset_token"],
        "password": "UpdatedSecure!1",
    }
    assert client.post(f"{BASE}/email/reset/complete", json={**completion, "password": "alllowercase"}).status_code == 400
    assert client.post(f"{BASE}/email/reset/complete", json=completion).status_code == 204
    assert mailbox[-1][1] == "Your HealthLink password was updated"
    assert client.post(f"{BASE}/email/reset/complete", json=completion).status_code == 400
    assert client.get("/api/v1/citizens/me", headers=headers).status_code == 401
    client.cookies.set(REFRESH_TOKEN_COOKIE_NAME, refresh_cookie)
    assert client.post(f"{BASE}/refresh").status_code == 401
    assert client.post(f"{BASE}/citizen/login", json=sign_in).status_code == 401
    assert client.post(f"{BASE}/citizen/login", json={**sign_in, "password": completion["password"]}).status_code == 200


def test_professional_role_and_admin_recovery_routing(client, db_session, mailbox, monkeypatch):
    now = datetime.now(UTC)
    monkeypatch.setattr(email_codes, "utc_now", lambda: now)
    payload = professional_payload()
    request = client.post(f"{BASE}/email/signup", json={"email": payload["email"], "portal": "PROFESSIONAL"})
    assert client.post(f"{BASE}/professional/register", json={
        **payload, "challenge_id": request.json()["challenge_id"], "code": _code(mailbox),
    }).status_code == 201
    admin = create_trusted_admin(db_session, email="trusted@example.com", password="SecureAdmin!123",
                                 first_name="Trusted", last_name="Admin")
    admin.user.email_verified_at = now
    db_session.commit()
    now += timedelta(seconds=61)

    wrong = {"portal": "PROFESSIONAL", "nid_number": payload["nid_number"], "role_code": "NURSE"}
    assert client.post(f"{BASE}/email/reset", json=wrong).status_code == 202
    assert client.post(f"{BASE}/email/reset", json={"portal": "CITIZEN", "email": admin.user.email}).status_code == 202
    assert len(mailbox) == 1
    for identity, recipient in (
        ({**wrong, "role_code": "DOCTOR"}, payload["email"]),
        ({"portal": "ADMIN", "email": admin.user.email}, admin.user.email),
    ):
        challenge = client.post(f"{BASE}/email/reset", json=identity)
        assert challenge.status_code == 202
        assert mailbox[-1][0] == recipient
        assert client.post(f"{BASE}/email/reset/verify", json={
            "challenge_id": challenge.json()["challenge_id"], "code": _code(mailbox),
        }).status_code == 200


def test_resend_cooldown_attempt_limit_and_expiry(client, mailbox, monkeypatch):
    now = datetime.now(UTC)
    monkeypatch.setattr(email_codes, "utc_now", lambda: now)
    payload = registration_payload()
    request = {"email": payload["email"], "portal": "CITIZEN"}
    start = client.post(f"{BASE}/email/signup", json=request)
    original = {"challenge_id": start.json()["challenge_id"], "code": _code(mailbox)}
    assert client.post(f"{BASE}/email/signup", json=request).status_code == 429
    now += timedelta(seconds=61)
    resend = client.post(f"{BASE}/email/signup", json=request)
    assert resend.status_code == 202
    assert client.post(f"{BASE}/citizen/register", json={**payload, **original}).status_code == 400
    current = {"challenge_id": resend.json()["challenge_id"], "code": _code(mailbox)}
    wrong = "000000" if current["code"] != "000000" else "111111"
    for _ in range(5):
        assert client.post(f"{BASE}/citizen/register", json={**payload, **current, "code": wrong}).status_code == 400
    assert client.post(f"{BASE}/citizen/register", json={**payload, **current}).status_code == 400
    now += timedelta(seconds=61)
    resend = client.post(f"{BASE}/email/signup", json=request)
    now += timedelta(minutes=10)
    assert client.post(f"{BASE}/citizen/register", json={
        **payload, "challenge_id": resend.json()["challenge_id"], "code": _code(mailbox),
    }).status_code == 400
