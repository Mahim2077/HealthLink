from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.admins.models import AdminActionLog
from app.admins.verification_repository import ProfessionalVerificationRepository
from app.admins.verification_schemas import (
    ProfessionalRegistrationDetail,
    ProfessionalRegistrationSummary,
)
from app.auth.service import utc_now
from app.core.exceptions import HealthLinkError
from app.facilities.repository import FacilityRepository
from app.professionals.constants import VerificationStatus
from app.professionals.models import ProfessionalRoleRegistration


class ProfessionalRegistrationNotFoundError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Professional role registration not found.", status_code=404)


class VerificationConflictError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Only a pending registration can be reviewed.", status_code=409)


class FacilityUnavailableError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("An active healthcare facility is required.", status_code=409)


class ProfessionalVerificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ProfessionalVerificationRepository(db)
        self.facilities = FacilityRepository(db)

    @staticmethod
    def _summary(
        registration: ProfessionalRoleRegistration,
    ) -> ProfessionalRegistrationSummary:
        user = registration.professional.user
        return ProfessionalRegistrationSummary(
            id=registration.id,
            professional_id=registration.professional_id,
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role_code=registration.role.code,
            role_name=registration.role.name,
            facility_name_submitted=registration.facility_name_submitted,
            designation=registration.designation,
            verification_status=registration.verification_status,
            submitted_at=registration.submitted_at,
        )

    def _detail(
        self, registration: ProfessionalRoleRegistration
    ) -> ProfessionalRegistrationDetail:
        summary = self._summary(registration)
        doctor_detail = self.repository.get_doctor_detail(registration.id)
        return ProfessionalRegistrationDetail(
            **summary.model_dump(),
            additional_info=registration.additional_info,
            bmdc_registration_number=(
                doctor_detail.bmdc_registration_number if doctor_detail else None
            ),
            facility=registration.facility,
            verified_at=registration.verified_at,
            verified_by=registration.verified_by,
            rejected_at=registration.rejected_at,
            rejection_reason=registration.rejection_reason,
        )

    def list_registrations(
        self, status: VerificationStatus | None
    ) -> list[ProfessionalRegistrationSummary]:
        return [self._summary(row) for row in self.repository.list(status)]

    def get_registration(
        self, registration_id: uuid.UUID
    ) -> ProfessionalRegistrationDetail:
        registration = self.repository.get_by_id(registration_id)
        if registration is None:
            raise ProfessionalRegistrationNotFoundError()
        return self._detail(registration)

    def verify(
        self,
        registration_id: uuid.UUID,
        facility_id: uuid.UUID,
        *,
        admin_user_id: uuid.UUID,
    ) -> ProfessionalRegistrationDetail:
        registration = self._pending_for_update(registration_id)
        facility = self.facilities.get_by_id(facility_id, for_update=True)
        if facility is None or not facility.is_active:
            raise FacilityUnavailableError()
        now = utc_now()
        registration.facility_id = facility.id
        registration.verification_status = VerificationStatus.VERIFIED.value
        registration.verified_at = now
        registration.verified_by = admin_user_id
        registration.rejected_at = None
        registration.rejection_reason = None
        self._audit(registration, admin_user_id, "PROFESSIONAL_VERIFY")
        self.db.commit()
        return self.get_registration(registration.id)

    def reject(
        self,
        registration_id: uuid.UUID,
        reason: str,
        *,
        admin_user_id: uuid.UUID,
    ) -> ProfessionalRegistrationDetail:
        registration = self._pending_for_update(registration_id)
        registration.verification_status = VerificationStatus.REJECTED.value
        registration.facility_id = None
        registration.verified_at = None
        registration.verified_by = None
        registration.rejected_at = utc_now()
        registration.rejection_reason = reason
        self._audit(
            registration,
            admin_user_id,
            "PROFESSIONAL_REJECT",
            reason=reason,
        )
        self.db.commit()
        return self.get_registration(registration.id)

    def _pending_for_update(
        self, registration_id: uuid.UUID
    ) -> ProfessionalRoleRegistration:
        registration = self.repository.get_by_id(registration_id, for_update=True)
        if registration is None:
            raise ProfessionalRegistrationNotFoundError()
        if registration.verification_status != VerificationStatus.PENDING.value:
            raise VerificationConflictError()
        return registration

    def _audit(
        self,
        registration: ProfessionalRoleRegistration,
        admin_user_id: uuid.UUID,
        action_type: str,
        *,
        reason: str | None = None,
    ) -> None:
        self.db.add(
            AdminActionLog(
                admin_user_id=admin_user_id,
                action_type=action_type,
                target_user_id=registration.professional.user_id,
                target_resource_type="PROFESSIONAL_ROLE_REGISTRATION",
                target_resource_id=registration.id,
                reason=reason,
            )
        )
