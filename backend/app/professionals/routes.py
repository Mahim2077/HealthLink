from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext, get_current_auth_context
from app.core.config import Settings
from app.db.session import get_db
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.schemas import (
    ProfessionalApplicationResponse,
    ProfessionalOnboardingRequest,
    ProfessionalRegistrationRequest,
)
from app.professionals.service import ProfessionalService, SubmittedProfessionalApplication


auth_router = APIRouter(prefix="/auth/professional", tags=["professional-auth"])
professional_router = APIRouter(prefix="/professionals", tags=["professionals"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _response(
    result: SubmittedProfessionalApplication,
) -> ProfessionalApplicationResponse:
    return ProfessionalApplicationResponse(
        user_id=result.user.id,
        professional_id=result.profile.id,
        role_registration_id=result.registration.id,
        role_code=ProfessionalRoleCode(result.role.code),
        verification_status=VerificationStatus(result.registration.verification_status),
        submitted_at=result.registration.submitted_at,
    )


@auth_router.post(
    "/register",
    response_model=ProfessionalApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_professional(
    payload: ProfessionalRegistrationRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> ProfessionalApplicationResponse:
    return _response(ProfessionalService(db, _settings(request)).register_new(payload))


@professional_router.post(
    "/me/onboard",
    response_model=ProfessionalApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def onboard_professional_role(
    payload: ProfessionalOnboardingRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> ProfessionalApplicationResponse:
    return _response(
        ProfessionalService(db, _settings(request)).onboard_existing(
            context.user.id,
            payload,
        )
    )
