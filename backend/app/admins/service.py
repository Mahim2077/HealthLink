from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.admins.models import AdminAccount
from app.admins.repository import AdminRepository
from app.admins.schemas import AdminLoginRequest
from app.auth.constants import Portal
from app.auth.service import AuthenticationError, AuthService, IssuedTokens
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.core.security import verify_password


_DUMMY_ADMIN_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "x6UEndDIGINbChliFokAwg$WMEeIYWIpGqFiUdzYGg6peAi29r+B7mSRpjNdS6jsqU"
)


class AdminCapabilityError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Active administrator account required.", status_code=403)


class AdminService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = AdminRepository(db)

    def login(self, request: AdminLoginRequest) -> IssuedTokens:
        email = str(request.email).strip().lower()
        user = self.repository.get_user_by_email(email)
        password_matches = verify_password(
            request.password.get_secret_value(),
            user.password_hash if user is not None else _DUMMY_ADMIN_PASSWORD_HASH,
        )
        admin = (
            self.repository.get_admin_by_user_id(user.id)
            if user is not None
            else None
        )
        if (
            user is None
            or not user.is_active
            or not password_matches
            or admin is None
            or not admin.is_active
        ):
            raise AuthenticationError("Invalid email or password.")
        return AuthService(self.db, self.settings).create_session(user.id, Portal.ADMIN)

    def require_active_admin(self, user_id: uuid.UUID) -> AdminAccount:
        admin = self.repository.get_admin_by_user_id(user_id)
        if admin is None or not admin.is_active:
            raise AdminCapabilityError()
        return admin
