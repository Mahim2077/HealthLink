from typing import Annotated

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.admins.identity_schemas import (
    CitizenIdentityCorrectionRequest,
    CitizenIdentityCorrectionResponse,
    CitizenIdentityDetail,
    CitizenIdentitySearchQuery,
    CitizenIdentitySummary,
)
from app.admins.identity_service import CitizenIdentitySupportService
from app.admins.schemas import AdminLoginRequest, AdminMeResponse
from app.admins.service import AdminService
from app.admins.verification_schemas import (
    ProfessionalRegistrationDetail,
    ProfessionalRegistrationSummary,
    RejectProfessionalRequest,
    VerifyProfessionalRequest,
)
from app.admins.verification_service import ProfessionalVerificationService
from app.auth.constants import Portal
from app.auth.cookies import set_refresh_cookie
from app.auth.dependencies import AuthContext, require_portal
from app.auth.schemas import TokenResponse
from app.core.config import Settings
from app.db.session import get_db
from app.facilities.schemas import FacilityResponse, FacilityWriteRequest
from app.facilities.service import FacilityService
from app.professionals.constants import VerificationStatus


auth_router = APIRouter(prefix="/auth/admin", tags=["admin-auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@auth_router.post("/login", response_model=TokenResponse)
def login_admin(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    settings = _settings(request)
    tokens = AdminService(db, settings).login(payload)
    set_refresh_cookie(response, tokens.refresh_token, tokens.refresh_token_expires_at, settings)
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.access_token_expires_in,
        portal=tokens.portal,
    )


@admin_router.get("/me", response_model=AdminMeResponse)
def get_admin_me(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> AdminMeResponse:
    admin = AdminService(db, _settings(request)).require_active_admin(context.user.id)
    return AdminMeResponse(
        user_id=context.user.id,
        admin_id=admin.id,
        email=context.user.email,
        first_name=context.user.first_name,
        last_name=context.user.last_name,
        is_super_admin=admin.is_super_admin,
    )


def _require_active_admin(
    request: Request, db: Session, context: AuthContext
) -> None:
    AdminService(db, _settings(request)).require_active_admin(context.user.id)


@admin_router.get(
    "/professional-registrations",
    response_model=list[ProfessionalRegistrationSummary],
)
def list_professional_registrations(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
    verification_status: Annotated[VerificationStatus | None, Query()] = None,
) -> list[ProfessionalRegistrationSummary]:
    _require_active_admin(request, db, context)
    return ProfessionalVerificationService(db).list_registrations(
        verification_status
    )


@admin_router.get(
    "/professional-registrations/{registration_id}",
    response_model=ProfessionalRegistrationDetail,
)
def get_professional_registration(
    registration_id: uuid.UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> ProfessionalRegistrationDetail:
    _require_active_admin(request, db, context)
    return ProfessionalVerificationService(db).get_registration(registration_id)


@admin_router.post(
    "/professional-registrations/{registration_id}/verify",
    response_model=ProfessionalRegistrationDetail,
)
def verify_professional_registration(
    registration_id: uuid.UUID,
    payload: VerifyProfessionalRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> ProfessionalRegistrationDetail:
    _require_active_admin(request, db, context)
    return ProfessionalVerificationService(db).verify(
        registration_id,
        payload.facility_id,
        admin_user_id=context.user.id,
    )


@admin_router.post(
    "/professional-registrations/{registration_id}/reject",
    response_model=ProfessionalRegistrationDetail,
)
def reject_professional_registration(
    registration_id: uuid.UUID,
    payload: RejectProfessionalRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> ProfessionalRegistrationDetail:
    _require_active_admin(request, db, context)
    return ProfessionalVerificationService(db).reject(
        registration_id,
        payload.reason,
        admin_user_id=context.user.id,
    )


@admin_router.get("/facilities", response_model=list[FacilityResponse])
def list_facilities(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> list[FacilityResponse]:
    _require_active_admin(request, db, context)
    return [
        FacilityResponse.model_validate(facility)
        for facility in FacilityService(db).list_facilities()
    ]


@admin_router.post(
    "/facilities",
    response_model=FacilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_facility(
    payload: FacilityWriteRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> FacilityResponse:
    _require_active_admin(request, db, context)
    facility = FacilityService(db).create(payload, admin_user_id=context.user.id)
    return FacilityResponse.model_validate(facility)


@admin_router.put("/facilities/{facility_id}", response_model=FacilityResponse)
def update_facility(
    facility_id: uuid.UUID,
    payload: FacilityWriteRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> FacilityResponse:
    _require_active_admin(request, db, context)
    facility = FacilityService(db).update(
        facility_id, payload, admin_user_id=context.user.id
    )
    return FacilityResponse.model_validate(facility)


@admin_router.get(
    "/citizen-identities/search",
    response_model=list[CitizenIdentitySummary],
)
def search_citizen_identities(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
    query: Annotated[
        CitizenIdentitySearchQuery,
        Depends(CitizenIdentitySearchQuery.as_query),
    ],
) -> list[CitizenIdentitySummary]:
    _require_active_admin(request, db, context)
    return CitizenIdentitySupportService(db).search(
        nid_number=query.nid_number,
        birth_certificate_number=query.birth_certificate_number,
        email=str(query.email) if query.email else None,
        user_id=query.user_id,
        limit=query.limit,
    )


@admin_router.get(
    "/citizen-identities/{user_id}",
    response_model=CitizenIdentityDetail,
)
def get_citizen_identity(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> CitizenIdentityDetail:
    _require_active_admin(request, db, context)
    return CitizenIdentitySupportService(db).detail(user_id)


@admin_router.post(
    "/citizen-identities/{user_id}/correct",
    response_model=CitizenIdentityCorrectionResponse,
)
def correct_citizen_identity(
    user_id: uuid.UUID,
    payload: CitizenIdentityCorrectionRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[AuthContext, Depends(require_portal(Portal.ADMIN))],
) -> CitizenIdentityCorrectionResponse:
    _require_active_admin(request, db, context)
    return CitizenIdentitySupportService(db).correct(
        user_id,
        payload,
        admin_user_id=context.user.id,
    )
