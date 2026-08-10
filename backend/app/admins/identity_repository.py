from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth.models import AuthSession, User
from app.citizens.models import (
    CitizenIdentifier,
    CitizenProfile,
    UserNationalIdentifier,
)


class CitizenIdentitySupportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        *,
        nid_number: str | None,
        birth_certificate_number: str | None,
        email: str | None,
        user_id: uuid.UUID | None,
        limit: int,
    ) -> list[User]:
        # Build a single SQL with all filters at once; only invoke when the caller
        # actually supplied at least one filter (the route enforces this).
        statement = (
            select(User)
            .join(CitizenIdentifier, CitizenIdentifier.user_id == User.id)
            .options(
                selectinload(User.auth_sessions),
            )
            .distinct()
        )

        if user_id is not None:
            statement = statement.where(User.id == user_id)
        if email is not None:
            statement = statement.where(User.email == email.lower())
        if nid_number is not None:
            statement = statement.join(
                UserNationalIdentifier,
                UserNationalIdentifier.user_id == User.id,
            ).where(UserNationalIdentifier.nid_number == nid_number)
        if birth_certificate_number is not None:
            statement = statement.where(
                CitizenIdentifier.birth_certificate_number == birth_certificate_number
            )

        statement = statement.order_by(User.created_at, User.id).limit(limit)
        return list(self.db.scalars(statement).unique())

    def get_user_with_identity(self, user_id: uuid.UUID) -> User | None:
        statement = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.auth_sessions),
            )
        )
        return self.db.scalar(statement)

    def get_national_identifier_by_user_id(
        self, user_id: uuid.UUID, *, for_update: bool = False
    ) -> UserNationalIdentifier | None:
        statement = select(UserNationalIdentifier).where(
            UserNationalIdentifier.user_id == user_id
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.db.scalar(statement)

    def get_national_identifier_by_number(
        self, nid_number: str
    ) -> UserNationalIdentifier | None:
        return self.db.scalar(
            select(UserNationalIdentifier).where(
                UserNationalIdentifier.nid_number == nid_number
            )
        )

    def get_national_identifier_by_id(
        self, identifier_id: uuid.UUID
    ) -> UserNationalIdentifier | None:
        return self.db.get(UserNationalIdentifier, identifier_id)

    def get_identity_by_user_id(
        self, user_id: uuid.UUID, *, for_update: bool = False
    ) -> CitizenIdentifier | None:
        statement = select(CitizenIdentifier).where(
            CitizenIdentifier.user_id == user_id
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.db.scalar(statement)

    def get_identity_by_birth_certificate(
        self, birth_certificate_number: str
    ) -> CitizenIdentifier | None:
        return self.db.scalar(
            select(CitizenIdentifier).where(
                CitizenIdentifier.birth_certificate_number == birth_certificate_number
            )
        )

    def get_profile_by_user_id(self, user_id: uuid.UUID) -> CitizenProfile | None:
        return self.db.scalar(
            select(CitizenProfile).where(CitizenProfile.user_id == user_id)
        )

    def count_active_auth_sessions(self, user_id: uuid.UUID) -> int:
        return self.db.scalar(
            select(func.count())
            .select_from(AuthSession)
            .where(AuthSession.user_id == user_id)
            .where(AuthSession.revoked_at.is_(None))
        ) or 0
