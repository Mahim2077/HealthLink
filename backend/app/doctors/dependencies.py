from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from app.auth.constants import Portal
from app.auth.dependencies import (
    AuthContext,
    AuthorizationError,
    get_current_auth_context,
)
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.dependencies import (
    ProfessionalAuthContext,
    require_verified_professional_role,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.professionals.models import ProfessionalRoleRegistration


_CITIZEN_OR_ADMIN_PORTALS = frozenset({Portal.CITIZEN, Portal.ADMIN})


@dataclass(frozen=True)
class AuthenticatedPortal:
    """Context returned to doctor discovery endpoints.

    V6 §13 allows any authenticated HealthLink user (citizen or admin) to
    search doctors. ``portal`` reflects the active session portal.
    """

    auth: AuthContext
    portal: Portal


def require_citizen_or_admin_portal() -> Callable[..., AuthenticatedPortal]:
    """FastAPI dependency yielding an authenticated citizen or admin."""

    def _dependency(
        auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    ) -> AuthenticatedPortal:
        if auth.session.portal not in _CITIZEN_OR_ADMIN_PORTALS:
            raise AuthorizationError(
                "Citizen or admin portal required for doctor discovery."
            )
        return AuthenticatedPortal(auth=auth, portal=auth.session.portal)

    return _dependency


@dataclass(frozen=True)
class DoctorContext:
    """Context returned by the verified-doctor dependency."""

    auth: AuthContext
    doctor_user_id: uuid.UUID
    role_registration: "ProfessionalRoleRegistration"


def require_verified_doctor() -> Callable[..., DoctorContext]:
    """FastAPI dependency yielding a verified doctor context."""

    base_dependency = require_verified_professional_role(ProfessionalRoleCode.DOCTOR)

    def _dependency(
        context: Annotated[ProfessionalAuthContext, Depends(base_dependency)],
    ) -> DoctorContext:
        return DoctorContext(
            auth=context.auth,
            doctor_user_id=context.auth.user.id,
            role_registration=context.role_registration,
        )

    return _dependency
