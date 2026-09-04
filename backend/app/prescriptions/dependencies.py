from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.dependencies import (
    AuthContext,
    AuthorizationError,
    get_current_auth_context,
)
from app.auth.service import AuthenticationError
from app.citizens.repository import CitizenRepository
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.prescriptions.repository import PrescriptionsRepository
from app.professionals.constants import (
    ProfessionalRoleCode,
    VerificationStatus,
)
from app.professionals.repository import ProfessionalRepository


@dataclass(frozen=True)
class PrescriptionAccess:
    """Authorized actor context for the canonical prescription endpoints."""

    auth: AuthContext
    prescription_id: uuid.UUID
    actor_kind: Literal["citizen", "author_doctor"]
    citizen_profile_id: uuid.UUID | None = None
    doctor_role_registration_id: uuid.UUID | None = None


def get_prescription_access(
    prescription_id: Annotated[uuid.UUID, Path(...)],
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionAccess:
    """Allow only the owning citizen or the verified author doctor."""

    prescription = PrescriptionsRepository(db).get_prescription_by_id(
        prescription_id
    )
    if prescription is None:
        raise HealthLinkError("Prescription not found.", status_code=404)

    if auth.portal is Portal.CITIZEN:
        profile = CitizenRepository(db).get_profile_by_user_id(auth.user.id)
        if profile is None:
            raise AuthorizationError("Citizen profile required.")
        if prescription.citizen_id != profile.id:
            raise HealthLinkError("Prescription not found.", status_code=404)
        return PrescriptionAccess(
            auth=auth,
            prescription_id=prescription_id,
            actor_kind="citizen",
            citizen_profile_id=profile.id,
        )

    if auth.portal is Portal.PROFESSIONAL:
        session_role_id = auth.session.active_professional_role_registration_id
        claim_role_id = auth.claims.active_professional_role_registration_id
        if (
            session_role_id is None
            or claim_role_id is None
            or session_role_id != claim_role_id
        ):
            raise AuthenticationError("Invalid professional role context.")

        registration = ProfessionalRepository(
            db
        ).get_role_registration_by_id(session_role_id)
        if (
            registration is None
            or registration.professional.user_id != auth.user.id
        ):
            raise AuthenticationError("Invalid professional role context.")
        if (
            registration.verification_status
            != VerificationStatus.VERIFIED.value
            or not registration.role.is_active
            or registration.role.code != ProfessionalRoleCode.DOCTOR.value
        ):
            raise AuthorizationError("Verified doctor role required.")
        if prescription.author_doctor_role_registration_id != registration.id:
            raise AuthorizationError(
                "Only the author doctor may access this prescription."
            )
        return PrescriptionAccess(
            auth=auth,
            prescription_id=prescription_id,
            actor_kind="author_doctor",
            doctor_role_registration_id=registration.id,
        )

    raise AuthorizationError(
        "Citizen or verified author-doctor access required."
    )


__all__ = ["PrescriptionAccess", "get_prescription_access"]
