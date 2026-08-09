from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.admins.schemas import AdminLoginRequest, AdminMeResponse
from app.admins.service import AdminService
from app.auth.constants import Portal
from app.auth.cookies import set_refresh_cookie
from app.auth.dependencies import AuthContext, require_portal
from app.auth.schemas import TokenResponse
from app.core.config import Settings
from app.db.session import get_db


auth_router = APIRouter(prefix="/auth/admin", tags=["admin-auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@auth_router.post("/login", response_model=TokenResponse)
def login_admin(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    settings = _settings(request)
    tokens = AdminService(db, settings).login(payload)
    set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_token_expires_at, settings)
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.access_token_expires_in,
        portal=tokens.portal,
    )


@admin_router.get("/me", response_model=AdminMeResponse)
def get_admin_me(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> AdminMeResponse:
    admin = AdminService(db, _settings(request)).require_active_admin(context.user.id)
    return AdminMeResponse(
        user_id=context.user.id,
        admin_id=admin.id,
        email=context.user.email,
        first_name=context.user.first_name,
        last_name=context.user.last_name,
        is_super_admin=admin.is_super_admin,
    )
