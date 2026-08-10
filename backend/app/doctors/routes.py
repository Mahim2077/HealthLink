from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.doctors.dependencies import require_citizen_or_admin_portal, AuthenticatedPortal
from app.doctors.schemas import (
    DoctorProfile,
    DoctorSearchFilters,
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
    if not filters.has_filter():
        from fastapi.exceptions import RequestValidationError

        raise RequestValidationError(
            [
                {
                    "loc": ("query",),
                    "msg": "Provide at least one of name, facility_name, weekday.",
                    "type": "value_error.missing",
                }
            ]
        )
    return DoctorService(db, _settings(request)).search_doctors(
        name=filters.name,
        facility_name=filters.facility_name,
        weekday=filters.weekday.value if filters.weekday else None,
        limit=filters.limit,
    )


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