from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel, Field, ValidationError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.auth.constants import Portal
from app.core.config import Settings


REFRESH_TOKEN_COOKIE_NAME = "healthlink_refresh_token"
_PASSWORD_HASHER = PasswordHash.recommended()
_REQUIRED_ACCESS_TOKEN_CLAIMS = [
    "sub",
    "portal",
    "sid",
    "jti",
    "iat",
    "exp",
    "type",
]


class AccessTokenClaims(BaseModel):
    sub: uuid.UUID
    portal: Portal
    sid: uuid.UUID
    jti: uuid.UUID
    issued_at: datetime = Field(alias="iat")
    expires_at: datetime = Field(alias="exp")
    token_type: Literal["access"] = Field(alias="type")
    active_professional_role_registration_id: uuid.UUID | None = Field(
        default=None, alias="prrid"
    )


class TokenValidationError(ValueError):
    """Raised when an access token is missing required or valid claims."""


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password, password_hash)
    except (UnknownHashError, ValueError):
        return False


def generate_refresh_token() -> str:
    """Generate a high-entropy opaque refresh credential."""

    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def _jwt_secret(settings: Settings) -> str:
    if len(settings.jwt_secret_key) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters.")
    return settings.jwt_secret_key


def create_access_token(
    *,
    user_id: uuid.UUID,
    portal: Portal,
    session_id: uuid.UUID,
    settings: Settings,
    active_professional_role_registration_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "portal": portal.value,
        "sid": str(session_id),
        "jti": str(uuid.uuid4()),
        "iat": issued_at,
        "exp": expires_at,
        "type": "access",
    }
    if active_professional_role_registration_id is not None:
        payload["prrid"] = str(active_professional_role_registration_id)
    return jwt.encode(
        payload,
        _jwt_secret(settings),
        algorithm=settings.jwt_algorithm,
    )


def _decode_access_token(
    token: str,
    settings: Settings,
    *,
    allow_expired: bool,
) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(settings),
            algorithms=[settings.jwt_algorithm],
            options={
                "require": _REQUIRED_ACCESS_TOKEN_CLAIMS,
                "verify_exp": not allow_expired,
            },
        )
        return AccessTokenClaims.model_validate(payload)
    except (InvalidTokenError, ValidationError, ValueError) as error:
        raise TokenValidationError("Invalid or expired access token.") from error


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    return _decode_access_token(token, settings, allow_expired=False)


def decode_access_token_for_logout(
    token: str,
    settings: Settings,
) -> AccessTokenClaims:
    """Validate a signed access token as a session-revocation hint.

    Expiration is intentionally ignored because this function cannot authorize
    application access; it can only identify and revoke the token's own session.
    Signature, algorithm, token type, and all typed claims remain mandatory.
    """

    return _decode_access_token(token, settings, allow_expired=True)
