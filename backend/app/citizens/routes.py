from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.cookies import set_refresh_cookie
from app.auth.schemas import TokenResponse
from app.citizens.constants import CitizenRegistrationMethod
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.citizens.schemas import (
    CitizenIdentityResponse,
    CitizenAddNidRequest,
    CitizenLoginRequest,
    CitizenProfileResponse,
    CitizenProfileUpdateRequest,
    CitizenRegistrationRequest,
    CitizenRegistrationResponse,
)
from app.citizens.service import CitizenService
from app.core.config import Settings
from app.db.session import get_db


auth_router = APIRouter(prefix="/auth/citizen", tags=["citizen-auth"])
citizen_router = APIRouter(prefix="/citizens", tags=["citizens"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@auth_router.post(
    "/register",
    response_model=CitizenRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_citizen(
    payload: CitizenRegistrationRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> CitizenRegistrationResponse:
    registered = CitizenService(db, _settings(request)).register(payload)
    return CitizenRegistrationResponse(
        user_id=registered.user.id,
        citizen_id=registered.profile.id,
        email=registered.user.email,
        first_name=registered.user.first_name,
        last_name=registered.user.last_name,
        registered_with=CitizenRegistrationMethod(
            registered.identity.registered_with
        ),
        created_at=registered.user.created_at,
    )


@auth_router.post("/login", response_model=TokenResponse)
def login_citizen(
    payload: CitizenLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    settings = _settings(request)
    tokens = CitizenService(db, settings).login(payload)
    set_refresh_cookie(
        response,
        tokens.refresh_token,
        tokens.refresh_token_expires_at,
        settings,
    )
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.access_token_expires_in,
        portal=tokens.portal,
    )


@citizen_router.get("/me", response_model=CitizenProfileResponse)
def get_my_citizen_profile(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
) -> CitizenProfileResponse:
    profile = CitizenService(db, _settings(request)).get_profile(
        context.auth.user.id
    )
    return CitizenProfileResponse(
        user_id=context.auth.user.id,
        citizen_id=profile.id,
        email=context.auth.user.email,
        first_name=context.auth.user.first_name,
        last_name=context.auth.user.last_name,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        blood_group=profile.blood_group,
        address=profile.address,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@citizen_router.get("/me/identity", response_model=CitizenIdentityResponse)
def get_my_citizen_identity(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
) -> CitizenIdentityResponse:
    details = CitizenService(db, _settings(request)).get_identity(
        context.auth.user.id
    )
    return CitizenIdentityResponse(
        registered_with=CitizenRegistrationMethod(
            details.identity.registered_with
        ),
        nid_number=(
            details.national_identifier.nid_number
            if details.national_identifier is not None
            else None
        ),
        birth_certificate_number=details.identity.birth_certificate_number,
        nid_added_at=details.identity.nid_added_at,
    )


@citizen_router.put("/me/profile", response_model=CitizenProfileResponse)
def update_my_citizen_profile(
    payload: CitizenProfileUpdateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
) -> CitizenProfileResponse:
    profile = CitizenService(db, _settings(request)).update_profile(
        context.auth.user.id,
        payload,
    )
    return CitizenProfileResponse(
        user_id=context.auth.user.id,
        citizen_id=profile.id,
        email=context.auth.user.email,
        first_name=context.auth.user.first_name,
        last_name=context.auth.user.last_name,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        blood_group=profile.blood_group,
        address=profile.address,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@citizen_router.post(
    "/me/identity/add-nid",
    response_model=CitizenIdentityResponse,
)
def add_my_national_identifier(
    payload: CitizenAddNidRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
) -> CitizenIdentityResponse:
    details = CitizenService(db, _settings(request)).add_national_identifier(
        context.auth.user.id,
        payload,
    )
    return CitizenIdentityResponse(
        registered_with=CitizenRegistrationMethod(
            details.identity.registered_with
        ),
        nid_number=(
            details.national_identifier.nid_number
            if details.national_identifier is not None
            else None
        ),
        birth_certificate_number=details.identity.birth_certificate_number,
        nid_added_at=details.identity.nid_added_at,
    )
