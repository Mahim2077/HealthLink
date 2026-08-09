import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth.constants import Portal
from app.core.config import Settings
from app.core.security import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
    decode_access_token_for_logout,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_argon2_password_hash_and_verify() -> None:
    password = "correct horse battery staple"

    password_hash = hash_password(password)
    second_hash = hash_password(password)

    assert password_hash != password
    assert second_hash != password_hash
    assert password_hash.startswith("$argon2")
    assert verify_password(password, password_hash) is True
    assert verify_password("wrong password", password_hash) is False
    assert verify_password(password, "not-a-supported-hash") is False


def test_access_token_contains_shared_identity_portal_and_session_claims(
    test_settings: Settings,
) -> None:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    token = create_access_token(
        user_id=user_id,
        portal=Portal.PROFESSIONAL,
        session_id=session_id,
        settings=test_settings,
    )
    claims = decode_access_token(token, test_settings)

    assert claims.sub == user_id
    assert claims.sid == session_id
    assert claims.portal is Portal.PROFESSIONAL
    assert claims.token_type == "access"


def test_expired_access_token_is_rejected(test_settings: Settings) -> None:
    token = create_access_token(
        user_id=uuid.uuid4(),
        portal=Portal.CITIZEN,
        session_id=uuid.uuid4(),
        settings=test_settings,
        now=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token, test_settings)

    logout_claims = decode_access_token_for_logout(token, test_settings)
    assert logout_claims.token_type == "access"


def test_access_token_with_wrong_signature_is_rejected(
    test_settings: Settings,
) -> None:
    other_settings = test_settings.model_copy(
        update={"jwt_secret_key": "different-secret-key-with-at-least-thirty-two-characters"}
    )
    token = create_access_token(
        user_id=uuid.uuid4(),
        portal=Portal.ADMIN,
        session_id=uuid.uuid4(),
        settings=other_settings,
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token, test_settings)


def test_tampered_access_token_is_rejected(test_settings: Settings) -> None:
    token = create_access_token(
        user_id=uuid.uuid4(),
        portal=Portal.CITIZEN,
        session_id=uuid.uuid4(),
        settings=test_settings,
    )
    header, payload, signature = token.split(".")
    tampered_payload = ("A" if payload[0] != "A" else "B") + payload[1:]

    with pytest.raises(TokenValidationError):
        decode_access_token(
            ".".join((header, tampered_payload, signature)),
            test_settings,
        )


def test_access_token_signed_with_unapproved_algorithm_is_rejected(
    test_settings: Settings,
) -> None:
    valid_token = create_access_token(
        user_id=uuid.uuid4(),
        portal=Portal.ADMIN,
        session_id=uuid.uuid4(),
        settings=test_settings,
    )
    payload = jwt.decode(valid_token, options={"verify_signature": False})
    wrong_algorithm_token = jwt.encode(
        payload,
        test_settings.jwt_secret_key,
        algorithm="HS384",
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(wrong_algorithm_token, test_settings)


@pytest.mark.parametrize(
    "payload_update,removed_claim",
    [
        ({}, "sid"),
        ({"portal": "UNKNOWN"}, None),
        ({"type": "refresh"}, None),
        ({"sub": "not-a-uuid"}, None),
    ],
)
def test_missing_or_malformed_access_token_claims_are_rejected(
    test_settings: Settings,
    payload_update: dict[str, str],
    removed_claim: str | None,
) -> None:
    valid_token = create_access_token(
        user_id=uuid.uuid4(),
        portal=Portal.CITIZEN,
        session_id=uuid.uuid4(),
        settings=test_settings,
    )
    payload = jwt.decode(valid_token, options={"verify_signature": False})
    payload.update(payload_update)
    if removed_claim is not None:
        payload.pop(removed_claim)
    malformed_token = jwt.encode(
        payload,
        test_settings.jwt_secret_key,
        algorithm=test_settings.jwt_algorithm,
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(malformed_token, test_settings)


def test_refresh_tokens_are_opaque_and_only_deterministic_hashes_are_stored() -> None:
    first_token = generate_refresh_token()
    second_token = generate_refresh_token()

    assert first_token != second_token
    assert len(first_token) >= 64
    assert hash_refresh_token(first_token) == hash_refresh_token(first_token)
    assert hash_refresh_token(first_token) != hash_refresh_token(second_token)
    assert first_token not in hash_refresh_token(first_token)
