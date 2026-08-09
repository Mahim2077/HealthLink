from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, require_portal
from app.citizens.models import CitizenProfile
from app.citizens.repository import CitizenRepository
from app.citizens.service import CitizenCapabilityError
from app.db.session import get_db


@dataclass(frozen=True)
class CitizenContext:
    auth: AuthContext
    profile: CitizenProfile


def get_current_citizen(
    auth_context: Annotated[AuthContext, Depends(require_portal(Portal.CITIZEN))],
    db: Annotated[Session, Depends(get_db)],
) -> CitizenContext:
    profile = CitizenRepository(db).get_profile_by_user_id(auth_context.user.id)
    if profile is None:
        raise CitizenCapabilityError()
    return CitizenContext(auth=auth_context, profile=profile)
