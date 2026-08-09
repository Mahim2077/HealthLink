from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.citizens.models import (
    CitizenIdentifier,
    CitizenProfile,
    UserNationalIdentifier,
)


class CitizenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, instance):
        self.db.add(instance)
        return instance

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_profile_by_user_id(self, user_id: uuid.UUID) -> CitizenProfile | None:
        return self.db.scalar(
            select(CitizenProfile).where(CitizenProfile.user_id == user_id)
        )

    def get_identity_by_user_id(
        self,
        user_id: uuid.UUID,
    ) -> CitizenIdentifier | None:
        return self.db.scalar(
            select(CitizenIdentifier).where(CitizenIdentifier.user_id == user_id)
        )

    def get_national_identifier_by_number(
        self,
        nid_number: str,
    ) -> UserNationalIdentifier | None:
        return self.db.scalar(
            select(UserNationalIdentifier).where(
                UserNationalIdentifier.nid_number == nid_number
            )
        )

    def get_national_identifier_by_id(
        self,
        identifier_id: uuid.UUID,
    ) -> UserNationalIdentifier | None:
        return self.db.get(UserNationalIdentifier, identifier_id)

    def get_identity_by_birth_certificate(
        self,
        birth_certificate_number: str,
    ) -> CitizenIdentifier | None:
        return self.db.scalar(
            select(CitizenIdentifier).where(
                CitizenIdentifier.birth_certificate_number
                == birth_certificate_number
            )
        )
