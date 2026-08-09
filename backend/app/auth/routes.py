from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext, get_current_auth_context
from app.auth.schemas import TokenResponse
from app.auth.service import AuthService, AuthenticationError, IssuedTokens
from app.core.config import Settings
from app.core.security import (
    AccessTokenClaims,
    REFRESH_TOKEN_COOKIE_NAME,
    TokenValidationError,
    decode_access_token_for_logout,
)
from app.db.session import get_db


router = APIRouter(prefix="/auth", tags=["auth"])
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _set_refresh_cookie(
    response: Response,
    token: str,
    expires_at: datetime,
    settings: Settings,
) -> None:
    remaining_seconds = max(
        int((expires_at - datetime.now(expires_at.tzinfo)).total_seconds()),
        0,
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        expires=expires_at,
        max_age=remaining_seconds,
        path=_REFRESH_COOKIE_PATH,
        secure=settings.app_env in {"staging", "production"},
        httponly=True,
        samesite="lax",
    )


def _delete_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path=_REFRESH_COOKIE_PATH,
        secure=settings.app_env in {"staging", "production"},
        httponly=True,
        samesite="lax",
    )


def _token_response(tokens: IssuedTokens) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.access_token_expires_in,
        portal=tokens.portal,
    )


def _logout_access_claims(
    authorization: str | None,
    settings: Settings,
) -> AccessTokenClaims | None:
    if not authorization:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        return None
    try:
        return decode_access_token_for_logout(token.strip(), settings)
    except TokenValidationError:
        return None


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=REFRESH_TOKEN_COOKIE_NAME),
    ] = None,
) -> TokenResponse:
    if not refresh_token:
        raise AuthenticationError("Refresh token required.")

    settings = _settings(request)
    tokens = AuthService(db, settings).refresh_session(refresh_token)
    _set_refresh_cookie(
        response,
        tokens.refresh_token,
        tokens.refresh_token_expires_at,
        settings,
    )
    return _token_response(tokens)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[
        str | None,
        Cookie(alias=REFRESH_TOKEN_COOKIE_NAME),
    ] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    settings = _settings(request)
    AuthService(db, settings).logout_session(
        refresh_token,
        access_claims=_logout_access_claims(authorization, settings),
    )
    _delete_refresh_cookie(response, settings)


@router.post("/logout-all", status_code=204)
def logout_all(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> None:
    settings = _settings(request)
    AuthService(db, settings).logout_all(context.user.id)
    _delete_refresh_cookie(response, settings)
