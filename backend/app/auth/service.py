from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.models import AuthSession
from app.auth.repository import AuthRepository
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.core.security import (
    AccessTokenClaims,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


class AuthenticationError(HealthLinkError):
    def __init__(self, detail: str = "Authentication required.") -> None:
        super().__init__(
            detail,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    access_token_expires_in: int
    refresh_token_expires_at: datetime
    portal: Portal
    session_id: uuid.UUID


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = AuthRepository(db)

    def _issue_for_session(
        self,
        auth_session: AuthSession,
        raw_refresh_token: str,
        *,
        now: datetime,
    ) -> IssuedTokens:
        portal = Portal(auth_session.portal)
        access_token = create_access_token(
            user_id=auth_session.user_id,
            portal=portal,
            session_id=auth_session.id,
            settings=self.settings,
            now=now,
        )
        return IssuedTokens(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            access_token_expires_in=self.settings.access_token_expire_minutes * 60,
            refresh_token_expires_at=as_utc(auth_session.expires_at),
            portal=portal,
            session_id=auth_session.id,
        )

    def create_session(
        self,
        user_id: uuid.UUID,
        portal: Portal,
        *,
        now: datetime | None = None,
    ) -> IssuedTokens:
        issued_at = now or utc_now()
        user = self.repository.get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Active user account required.")

        raw_refresh_token = generate_refresh_token()
        auth_session = AuthSession(
            user_id=user_id,
            portal=portal.value,
            refresh_token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=issued_at
            + timedelta(days=self.settings.refresh_token_expire_days),
        )
        try:
            self.repository.add_session(auth_session)
            self.db.flush()
            issued_tokens = self._issue_for_session(
                auth_session,
                raw_refresh_token,
                now=issued_at,
            )
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def refresh_session(
        self,
        raw_refresh_token: str,
        *,
        now: datetime | None = None,
    ) -> IssuedTokens:
        refreshed_at = now or utc_now()
        token_hash = hash_refresh_token(raw_refresh_token)
        auth_session = self.repository.get_session_by_refresh_hash(
            token_hash,
            for_update=True,
        )
        if auth_session is None:
            raise AuthenticationError("Invalid or expired refresh token.")

        if auth_session.revoked_at is not None:
            raise AuthenticationError("Invalid or expired refresh token.")

        if as_utc(auth_session.expires_at) <= refreshed_at:
            auth_session.revoked_at = refreshed_at
            auth_session.last_used_at = refreshed_at
            self.db.commit()
            raise AuthenticationError("Invalid or expired refresh token.")

        user = self.repository.get_user_by_id(auth_session.user_id)
        if user is None or not user.is_active:
            self.repository.revoke_active_sessions(auth_session.user_id, refreshed_at)
            self.db.commit()
            raise AuthenticationError("Active user account required.")

        next_refresh_token = generate_refresh_token()
        auth_session.last_used_at = refreshed_at
        auth_session.refresh_token_hash = hash_refresh_token(next_refresh_token)
        try:
            self.db.flush()
            issued_tokens = self._issue_for_session(
                auth_session,
                next_refresh_token,
                now=refreshed_at,
            )
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def logout_session(
        self,
        raw_refresh_token: str | None,
        *,
        access_claims: AccessTokenClaims | None = None,
        now: datetime | None = None,
    ) -> None:
        revoked_at = now or utc_now()

        if access_claims is not None:
            auth_session = self.repository.get_session_by_id(
                access_claims.sid,
                for_update=True,
            )
            if (
                auth_session is not None
                and auth_session.user_id == access_claims.sub
                and auth_session.portal == access_claims.portal.value
            ):
                if auth_session.revoked_at is None:
                    auth_session.revoked_at = revoked_at

        if raw_refresh_token:
            auth_session = self.repository.get_session_by_refresh_hash(
                hash_refresh_token(raw_refresh_token),
                for_update=True,
            )
            if auth_session is not None and auth_session.revoked_at is None:
                auth_session.revoked_at = revoked_at
        self.db.commit()

    def logout_by_refresh_token(
        self,
        raw_refresh_token: str | None,
        *,
        now: datetime | None = None,
    ) -> None:
        """Compatibility wrapper for cookie-only callers and tests."""

        self.logout_session(raw_refresh_token, now=now)

    def logout_all(
        self,
        user_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> int:
        revoked_count = self.repository.revoke_active_sessions(
            user_id,
            now or utc_now(),
        )
        self.db.commit()
        return revoked_count
