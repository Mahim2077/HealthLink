from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext, get_current_auth_context
from app.auth.cookies import set_refresh_cookie
from app.core.config import Settings
from app.db.session import get_db
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.schemas import (
    ProfessionalApplicationResponse,
    ProfessionalOnboardingRequest,
    ProfessionalRegistrationRequest,
    ProfessionalLoginRequest,
    ProfessionalLoginResponse,
    ProfessionalMeResponse,
)
from app.professionals.dependencies import (
    ProfessionalAuthContext,
    get_current_professional_context,
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


@auth_router.post("/login", response_model=ProfessionalLoginResponse)
def login_professional(
    payload: ProfessionalLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> ProfessionalLoginResponse:
    settings = _settings(request)
    result = ProfessionalService(db, settings).login(payload)
    set_refresh_cookie(
        response,
        result.tokens.refresh_token,
        result.tokens.refresh_token_expires_at,
        settings,
    )
    return ProfessionalLoginResponse(
        access_token=result.tokens.access_token,
        expires_in=result.tokens.access_token_expires_in,
        portal=result.tokens.portal,
        role_registration_id=result.registration.id,
        role_code=result.role.code,
        verification_status=result.registration.verification_status,
    )


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


@professional_router.get("/me", response_model=ProfessionalMeResponse)
def get_professional_me(
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_professional_context),
    ],
) -> ProfessionalMeResponse:
    registration = context.role_registration
    user = registration.professional.user
    return ProfessionalMeResponse(
        user_id=user.id,
        professional_id=registration.professional_id,
        role_registration_id=registration.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role_code=registration.role.code,
        role_name=registration.role.name,
        verification_status=registration.verification_status,
        designation=registration.designation,
        facility=registration.facility,
        submitted_at=registration.submitted_at,
        verified_at=registration.verified_at,
        rejected_at=registration.rejected_at,
        rejection_reason=registration.rejection_reason,
    )
