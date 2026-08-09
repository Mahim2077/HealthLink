from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.citizens.models import UserNationalIdentifier
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


class ProfessionalRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, instance):
        self.db.add(instance)
        return instance

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_user_by_id_for_update(self, user_id: uuid.UUID) -> User | None:
        return self.db.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def get_nid_by_number(self, nid_number: str) -> UserNationalIdentifier | None:
        return self.db.scalar(
            select(UserNationalIdentifier).where(
                UserNationalIdentifier.nid_number == nid_number
            )
        )

    def get_nid_by_user_id(self, user_id: uuid.UUID) -> UserNationalIdentifier | None:
        return self.db.scalar(
            select(UserNationalIdentifier).where(
                UserNationalIdentifier.user_id == user_id
            )
        )

    def get_profile_by_user_id(
        self, user_id: uuid.UUID
    ) -> HealthcareProfessionalProfile | None:
        return self.db.scalar(
            select(HealthcareProfessionalProfile).where(
                HealthcareProfessionalProfile.user_id == user_id
            )
        )

    def get_role_by_code(self, code: str) -> ProfessionalRole | None:
        return self.db.scalar(
            select(ProfessionalRole).where(ProfessionalRole.code == code)
        )

    def get_role_registration(
        self,
        professional_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> ProfessionalRoleRegistration | None:
        return self.db.scalar(
            select(ProfessionalRoleRegistration).where(
                ProfessionalRoleRegistration.professional_id == professional_id,
                ProfessionalRoleRegistration.role_id == role_id,
            )
        )

    def get_doctor_detail_by_bmdc(
        self, number: str
    ) -> DoctorRegistrationDetail | None:
        return self.db.scalar(
            select(DoctorRegistrationDetail).where(
                DoctorRegistrationDetail.bmdc_registration_number == number
            )
        )
