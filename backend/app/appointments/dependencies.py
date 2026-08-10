from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, require_portal
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.db.session import get_db


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


def require_citizen_portal() -> Annotated[AuthContext, Depends(require_portal(Portal.CITIZEN))]:  # noqa: E501
    pass


__all__ = ["get_current_citizen_for_booking"]
