from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRoleRegistration,
)


class ProfessionalVerificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _load_options():
        return (
            selectinload(ProfessionalRoleRegistration.professional).selectinload(
                HealthcareProfessionalProfile.user
            ),
            selectinload(ProfessionalRoleRegistration.role),
            selectinload(ProfessionalRoleRegistration.facility),
        )

    def list(self, status: str | None) -> list[ProfessionalRoleRegistration]:
        statement = select(ProfessionalRoleRegistration).options(*self._load_options())
        if status is not None:
            statement = statement.where(
                ProfessionalRoleRegistration.verification_status == status
            )
        statement = statement.order_by(
            ProfessionalRoleRegistration.submitted_at,
            ProfessionalRoleRegistration.id,
        )
        return list(self.db.scalars(statement))

    def get_by_id(
        self, registration_id: uuid.UUID, *, for_update: bool = False
    ) -> ProfessionalRoleRegistration | None:
        statement = select(ProfessionalRoleRegistration).where(
            ProfessionalRoleRegistration.id == registration_id
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        registration = self.db.scalar(statement)
        if registration is not None:
            # Populate related display data after the row lock is held.
            registration = self.db.scalar(
                select(ProfessionalRoleRegistration)
                .where(ProfessionalRoleRegistration.id == registration_id)
                .options(*self._load_options())
                .execution_options(populate_existing=True)
            )
        return registration

    def get_doctor_detail(
        self, registration_id: uuid.UUID
    ) -> DoctorRegistrationDetail | None:
        return self.db.scalar(
            select(DoctorRegistrationDetail).where(
                DoctorRegistrationDetail.professional_role_registration_id
                == registration_id
            )
        )
