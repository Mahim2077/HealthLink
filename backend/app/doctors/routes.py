from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.doctors.dependencies import require_citizen_or_admin_portal, AuthenticatedPortal
from app.doctors.schemas import (
    DoctorFacilityOption,
    DoctorProfile,
    DoctorSearchFilters,
    DoctorSearchResponse,
    DoctorSummary,
    PracticeDay,
)
from app.doctors.service import DoctorService

doctor_router = APIRouter(prefix="/doctors", tags=["doctors"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@doctor_router.get(
    "",
    response_model=list[DoctorSummary],
    summary="Citizen-side doctor discovery",
)
def list_doctors(
    request: Request,
    filters: Annotated[DoctorSearchFilters, Query()],
    db: Annotated[Session, Depends(get_db)],
    portal: Annotated[
        AuthenticatedPortal, Depends(require_citizen_or_admin_portal())
    ],
) -> list[DoctorSummary]:
    del portal  # auth gate only — service operates against the DB
    response = DoctorService(db, _settings(request)).search_doctors(
        name=filters.name,
        facility_name=filters.facility_name,
        query=filters.query,
        specialization=(filters.specialization.value if filters.specialization else None),
        facility_id=filters.facility_id,
        weekday=filters.weekday.value if filters.weekday else None,
        sort=filters.sort,
        latitude=filters.latitude,
        longitude=filters.longitude,
        district_code=filters.district_code,
        upazila_code=filters.upazila_code,
        offset=filters.offset,
        limit=filters.limit,
    )
    return response.items


@doctor_router.post(
    "/search",
    response_model=DoctorSearchResponse,
    summary="Modern citizen doctor discovery",
)
def search_doctors(
    request: Request,
    filters: Annotated[DoctorSearchFilters, Body()],
    db: Annotated[Session, Depends(get_db)],
    portal: Annotated[
        AuthenticatedPortal, Depends(require_citizen_or_admin_portal())
    ],
) -> DoctorSearchResponse:
    del portal
    return DoctorService(db, _settings(request)).search_doctors(
        name=filters.name,
        facility_name=filters.facility_name,
        query=filters.query,
        specialization=(filters.specialization.value if filters.specialization else None),
        facility_id=filters.facility_id,
        weekday=filters.weekday.value if filters.weekday else None,
        sort=filters.sort,
        latitude=filters.latitude,
        longitude=filters.longitude,
        district_code=filters.district_code,
        upazila_code=filters.upazila_code,
        offset=filters.offset,
        limit=filters.limit,
    )


@doctor_router.get(
    "/facilities",
    response_model=list[DoctorFacilityOption],
    summary="Facility options for doctor discovery",
)
def list_discovery_facilities(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    portal: Annotated[
        AuthenticatedPortal, Depends(require_citizen_or_admin_portal())
    ],
) -> list[DoctorFacilityOption]:
    del portal
    return DoctorService(db, _settings(request)).list_discovery_facilities()


@doctor_router.get(
    "/{doctor_user_id}",
    response_model=DoctorProfile,
    summary="Citizen-side doctor profile",
)
def get_doctor_profile(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    portal: Annotated[
        AuthenticatedPortal, Depends(require_citizen_or_admin_portal())
    ],
    doctor_user_id: uuid.UUID = Path(...),
) -> DoctorProfile:
    del portal
    return DoctorService(db, _settings(request)).get_doctor_profile(doctor_user_id)


@doctor_router.get(
    "/{doctor_user_id}/practice-days",
    response_model=list[PracticeDay],
    summary="Citizen-side doctor practice schedule",
)
def get_doctor_practice_days(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    portal: Annotated[
        AuthenticatedPortal, Depends(require_citizen_or_admin_portal())
    ],
    doctor_user_id: uuid.UUID = Path(...),
) -> list[PracticeDay]:
    del portal
    return DoctorService(
        db, _settings(request)
    ).get_doctor_practice_days(doctor_user_id)
