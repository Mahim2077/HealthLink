from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.diagnostics.models import DiagnosticTest
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import HealthcareProfessionalProfile, ProfessionalRole, ProfessionalRoleRegistration


class DiagnosticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, item: DiagnosticTest) -> DiagnosticTest:
        self.db.add(item)
        return item

    def get(self, test_id: uuid.UUID, *, for_update: bool = False) -> DiagnosticTest | None:
        statement = select(DiagnosticTest).where(DiagnosticTest.id == test_id)
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return self.db.scalar(statement)

    def eligible_technicians(self, facility_id: uuid.UUID, search: str | None) -> list[dict]:
        statement = (
            select(ProfessionalRoleRegistration, User, HealthcareFacility)
            .join(ProfessionalRole, ProfessionalRole.id == ProfessionalRoleRegistration.role_id)
            .join(HealthcareProfessionalProfile, HealthcareProfessionalProfile.id == ProfessionalRoleRegistration.professional_id)
            .join(User, User.id == HealthcareProfessionalProfile.user_id)
            .join(HealthcareFacility, HealthcareFacility.id == ProfessionalRoleRegistration.facility_id)
            .where(
                ProfessionalRole.code == ProfessionalRoleCode.LAB_TECHNICIAN.value,
                ProfessionalRole.is_active.is_(True),
                User.is_active.is_(True),
                ProfessionalRoleRegistration.verification_status == VerificationStatus.VERIFIED.value,
                ProfessionalRoleRegistration.facility_id == facility_id,
                HealthcareFacility.is_active.is_(True),
            )
            .order_by(User.first_name, User.last_name, ProfessionalRoleRegistration.id)
            .limit(50)
        )
        if search:
            pattern = f"%{search}%"
            statement = statement.where(or_(User.first_name.ilike(pattern), User.last_name.ilike(pattern), ProfessionalRoleRegistration.designation.ilike(pattern)))
        return [
            {"registration": registration, "user": user, "facility": facility}
            for registration, user, facility in self.db.execute(statement).all()
        ]

    def technician(self, registration_id: uuid.UUID) -> tuple[ProfessionalRoleRegistration, User] | None:
        return self.db.execute(
            select(ProfessionalRoleRegistration, User)
            .join(ProfessionalRole, ProfessionalRole.id == ProfessionalRoleRegistration.role_id)
            .join(HealthcareProfessionalProfile, HealthcareProfessionalProfile.id == ProfessionalRoleRegistration.professional_id)
            .join(User, User.id == HealthcareProfessionalProfile.user_id)
            .where(
                ProfessionalRoleRegistration.id == registration_id,
                ProfessionalRole.code == ProfessionalRoleCode.LAB_TECHNICIAN.value,
                ProfessionalRole.is_active.is_(True),
                User.is_active.is_(True),
                ProfessionalRoleRegistration.verification_status == VerificationStatus.VERIFIED.value,
            )
        ).one_or_none()

    def list_for_citizen(self, citizen_id: uuid.UUID) -> list[DiagnosticTest]:
        return list(self.db.scalars(select(DiagnosticTest).where(DiagnosticTest.citizen_id == citizen_id).order_by(DiagnosticTest.created_at.desc(), DiagnosticTest.id.desc())))

    def list_for_registration(self, registration_id: uuid.UUID, role_code: str) -> list[DiagnosticTest]:
        field = DiagnosticTest.requested_by_role_registration_id if role_code == ProfessionalRoleCode.DOCTOR.value else DiagnosticTest.assigned_to_role_registration_id
        return list(self.db.scalars(select(DiagnosticTest).where(field == registration_id).order_by(DiagnosticTest.created_at.desc(), DiagnosticTest.id.desc())))

    def names(self, tests: list[DiagnosticTest]) -> dict[uuid.UUID, str]:
        ids = {test.requested_by_role_registration_id for test in tests} | {test.assigned_to_role_registration_id for test in tests if test.assigned_to_role_registration_id}
        if not ids:
            return {}
        rows = self.db.execute(select(ProfessionalRoleRegistration.id, User.first_name, User.last_name).join(HealthcareProfessionalProfile, HealthcareProfessionalProfile.id == ProfessionalRoleRegistration.professional_id).join(User, User.id == HealthcareProfessionalProfile.user_id).where(ProfessionalRoleRegistration.id.in_(ids))).all()
        return {row.id: " ".join(part for part in (row.first_name, row.last_name) if part).strip() for row in rows}

    def facilities(self, tests: list[DiagnosticTest]) -> dict[uuid.UUID, str]:
        ids = {test.facility_id for test in tests if test.facility_id}
        return dict(self.db.execute(select(HealthcareFacility.id, HealthcareFacility.name).where(HealthcareFacility.id.in_(ids))).all()) if ids else {}
