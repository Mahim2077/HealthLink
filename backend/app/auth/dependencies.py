from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.repository import AuthRepository
from app.auth.service import AuthenticationError, as_utc, utc_now
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.core.security import AccessTokenClaims, TokenValidationError, decode_access_token
from app.db.session import get_db


bearer_scheme = HTTPBearer(auto_error=False)


class AuthorizationError(HealthLinkError):
    def __init__(self, detail: str = "Insufficient permissions.") -> None:
        super().__init__(detail, status_code=403)


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession
    portal: Portal
    claims: AccessTokenClaims


def get_request_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_current_auth_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()

    try:
        claims = decode_access_token(credentials.credentials, settings)
    except TokenValidationError as error:
        raise AuthenticationError("Invalid or expired access token.") from error

    repository = AuthRepository(db)
    auth_session = repository.get_session_by_id(claims.sid)
    now = utc_now()
    if (
        auth_session is None
        or auth_session.user_id != claims.sub
        or auth_session.portal != claims.portal.value
        or auth_session.revoked_at is not None
        or as_utc(auth_session.expires_at) <= now
    ):
        raise AuthenticationError("Invalid or expired access token.")

    user = repository.get_user_by_id(claims.sub)
    if user is None or not user.is_active:
        raise AuthenticationError("Active user account required.")

    return AuthContext(
        user=user,
        session=auth_session,
        portal=claims.portal,
        claims=claims,
    )


def get_current_user(
    context: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> User:
    return context.user


def require_portal(portal: Portal) -> Callable[..., AuthContext]:
    """Return a dependency that enforces the access token's portal context."""

    def portal_dependency(
        context: Annotated[AuthContext, Depends(get_current_auth_context)],
    ) -> AuthContext:
        if context.portal is not portal:
            raise AuthorizationError(f"{portal.value} portal required.")
        return context

    return portal_dependency
