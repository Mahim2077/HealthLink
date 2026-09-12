from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.medical_records.schemas import MedicalHistoryPage, MedicalHistoryQuery
from app.medical_records.service import MedicalHistoryService
from app.visits.dependencies import (
    CurrentPatientAccess,
    get_current_patient_access_for_doctor,
)


citizen_medical_history_router = APIRouter(
    prefix="/citizens/me/medical-history",
    tags=["medical-history"],
)

professional_medical_history_router = APIRouter(
    prefix="/professionals/current-patient/medical-history",
    tags=["medical-history"],
)


@citizen_medical_history_router.get("", response_model=MedicalHistoryPage)
def list_my_medical_history(
    query: Annotated[MedicalHistoryQuery, Depends()],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
    db: Annotated[Session, Depends(get_db)],
) -> MedicalHistoryPage:
    _validate_date_range(query)
    return MedicalHistoryService(db).list_history(context.profile.id, query)


@professional_medical_history_router.get("", response_model=MedicalHistoryPage)
def list_current_patient_medical_history(
    query: Annotated[MedicalHistoryQuery, Depends()],
    access: Annotated[
        CurrentPatientAccess | None,
        Depends(get_current_patient_access_for_doctor),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> MedicalHistoryPage:
    _validate_date_range(query)
    if access is None:
        raise HealthLinkError(
            "No current chamber patient for the verified doctor.",
            status_code=404,
        )
    return MedicalHistoryService(db).list_history(
        access.context.citizen.id,
        query,
    )


def _validate_date_range(query: MedicalHistoryQuery) -> None:
    if (
        query.date_from is not None
        and query.date_to is not None
        and query.date_from > query.date_to
    ):
        raise HealthLinkError(
            "date_from must be on or before date_to.",
            status_code=422,
        )


__all__ = [
    "citizen_medical_history_router",
    "professional_medical_history_router",
]
