from datetime import datetime

from fastapi import Request, Response

from app.auth.constants import Portal
from app.auth.service import IssuedTokens
from app.core.config import Settings
from app.core.security import REFRESH_TOKEN_COOKIE_NAME


REFRESH_COOKIE_PATH = "/api/v1/auth"
SESSION_PORTAL_HEADER = "X-HealthLink-Portal"


def refresh_cookie_name(portal: Portal | None) -> str:
    if portal is None:
        return REFRESH_TOKEN_COOKIE_NAME
    return f"{REFRESH_TOKEN_COOKIE_NAME}_{portal.value.lower()}"


def set_sign_in_cookie(
    request: Request, response: Response, tokens: IssuedTokens, settings: Settings
) -> None:
    portal = tokens.portal if request.headers.get(SESSION_PORTAL_HEADER) == tokens.portal else None
    set_refresh_cookie(
        response, tokens.refresh_token, tokens.refresh_token_expires_at, settings, portal=portal
    )


def set_refresh_cookie(
    response: Response,
    token: str,
    expires_at: datetime,
    settings: Settings,
    *,
    portal: Portal | None = None,
) -> None:
    remaining_seconds = max(
        int((expires_at - datetime.now(expires_at.tzinfo)).total_seconds()),
        0,
    )
    response.set_cookie(
        key=refresh_cookie_name(portal),
        value=token,
        expires=expires_at,
        max_age=remaining_seconds,
        path=REFRESH_COOKIE_PATH,
        secure=settings.app_env in {"staging", "production"},
        httponly=True,
        samesite="lax",
    )


def delete_refresh_cookie(
    response: Response, settings: Settings, *, portal: Portal | None = None
) -> None:
    response.delete_cookie(
        key=refresh_cookie_name(portal),
        path=REFRESH_COOKIE_PATH,
        secure=settings.app_env in {"staging", "production"},
        httponly=True,
        samesite="lax",
    )
