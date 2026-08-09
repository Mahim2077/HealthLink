from datetime import datetime

from fastapi import Response

from app.core.config import Settings
from app.core.security import REFRESH_TOKEN_COOKIE_NAME


REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(
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
        path=REFRESH_COOKIE_PATH,
        secure=settings.app_env in {"staging", "production"},
        httponly=True,
        samesite="lax",
    )


def delete_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=settings.app_env in {"staging", "production"},
        httponly=True,
        samesite="lax",
    )
