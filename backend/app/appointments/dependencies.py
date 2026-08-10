from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, require_portal
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.db.session import get_db
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.dependencies import (
    ProfessionalAuthContext,
    require_verified_professional_role,
)


def get_current_citizen_for_booking(
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
    db: Annotated[Session, Depends(get_db)],
) -> CitizenContext:
    """Re-uses the canonical citizen dependency for booking endpoints.

    The repository looks the citizen profile up by ``auth.user.id`` so
    passing the context plus the live session is sufficient.
    """
    del db
    return context


def get_current_verified_doctor_for_chamber(
    context: Annotated[
        ProfessionalAuthContext,
        Depends(require_verified_professional_role(ProfessionalRoleCode.DOCTOR)),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> ProfessionalAuthContext:
    """Verified, DOCTOR-role professional with an open auth session.

    Used by every Phase 11 chamber endpoint. The doctor must have a
    verified DOCTOR role registration (already enforced by the
    dependency) and must reach the service through an authenticated
    PROFESSIONAL portal session, which is the only portal that carries
    the active-role registration in its claims.
    """
    del db
    return context


def require_citizen_portal() -> Annotated[AuthContext, Depends(require_portal(Portal.CITIZEN))]:
    pass


__all__ = [
    "get_current_citizen_for_booking",
    "get_current_verified_doctor_for_chamber",
]
