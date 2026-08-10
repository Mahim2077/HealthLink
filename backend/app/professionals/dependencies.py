from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, AuthorizationError, require_portal
from app.auth.service import AuthenticationError
from app.db.session import get_db
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import ProfessionalRoleRegistration
from app.professionals.repository import ProfessionalRepository


@dataclass(frozen=True)
class ProfessionalAuthContext:
    auth: AuthContext
    role_registration: ProfessionalRoleRegistration


def get_current_professional_context(
    auth: Annotated[AuthContext, Depends(require_portal(Portal.PROFESSIONAL))],
    db: Annotated[Session, Depends(get_db)],
) -> ProfessionalAuthContext:
    session_role_id = auth.session.active_professional_role_registration_id
    claim_role_id = auth.claims.active_professional_role_registration_id
    if session_role_id is None or claim_role_id is None or session_role_id != claim_role_id:
        raise AuthenticationError("Invalid professional role context.")
    registration = ProfessionalRepository(db).get_role_registration_by_id(
        session_role_id
    )
    if (
        registration is None
        or registration.professional.user_id != auth.user.id
    ):
        raise AuthenticationError("Invalid professional role context.")
    return ProfessionalAuthContext(auth=auth, role_registration=registration)


def require_verified_professional_role(
    *allowed_roles: ProfessionalRoleCode,
) -> Callable[..., ProfessionalAuthContext]:
    allowed = {role.value for role in allowed_roles}

    def dependency(
        context: Annotated[
            ProfessionalAuthContext,
            Depends(get_current_professional_context),
        ],
    ) -> ProfessionalAuthContext:
        registration = context.role_registration
        if (
            registration.verification_status != VerificationStatus.VERIFIED.value
            or not registration.role.is_active
            or (allowed and registration.role.code not in allowed)
        ):
            raise AuthorizationError("Verified professional role required.")
        return context

    return dependency
