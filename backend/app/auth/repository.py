from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def add_session(self, auth_session: AuthSession) -> AuthSession:
        self.db.add(auth_session)
        return auth_session

    def get_session_by_id(
        self,
        session_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AuthSession | None:
        if not for_update:
            return self.db.get(AuthSession, session_id)

        statement = (
            select(AuthSession)
            .where(AuthSession.id == session_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(statement)

    def get_session_by_refresh_hash(
        self,
        refresh_token_hash: str,
        *,
        for_update: bool = False,
    ) -> AuthSession | None:
        statement: Select[tuple[AuthSession]] = select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_token_hash
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def revoke_active_sessions(
        self,
        user_id: uuid.UUID,
        revoked_at: datetime,
    ) -> int:
        result = self.db.execute(
            update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        return int(result.rowcount or 0)
