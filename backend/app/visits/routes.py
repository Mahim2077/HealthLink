"""Phase 12 visits & prescriptions routes.

Implements the doctor's consultation workspace and the citizen read
path described in V6 sections 22-25. Doctor endpoints derive access
exclusively from the chamber queue (Phase 11's CURRENT queue row);
the manual ``patient_access_grants`` table is left untouched here
because Phase 14+ grants need their own wiring.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.visits.dependencies import (
    CurrentPatientAccess,
    get_current_patient_access_for_doctor,
    get_current_patient_access_for_queue_entry,
)
from app.visits.schemas import (
    CitizenVisitListResponse,
    DoctorCurrentPatientView,
    VisitDraftUpdateRequest,
    VisitDraftView,
)
from app.visits.service import (
    VisitsService,
    _current_patient_view,
)


doctor_visits_router = APIRouter(
    prefix="/doctors/me/visits",
    tags=["doctor-visits"],
)

citizen_visits_router = APIRouter(
    prefix="/citizens/me/visits",
    tags=["citizen-visits"],
)


@doctor_visits_router.get(
    "/current-patient",
    response_model=DoctorCurrentPatientView | None,
    summary="Verified doctor's current chamber patient (with optional draft visit)",
)
def get_current_patient(
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[
        CurrentPatientAccess | None,
        Depends(get_current_patient_access_for_doctor),
    ],
) -> DoctorCurrentPatientView | None:
    if access is None:
        return None
    return _current_patient_view(
        access.context, access_source=access.source
    )


@doctor_visits_router.post(
    "/start-for-current/{queue_id}",
    response_model=VisitDraftView,
    status_code=status.HTTP_200_OK,
    summary="Open (or re-open) the draft visit for the given CURRENT chamber queue row",
)
def start_visit_for_current(
    queue_id: Annotated[uuid.UUID, Path(...)],
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[
        CurrentPatientAccess,
        Depends(get_current_patient_access_for_queue_entry),
    ],
) -> VisitDraftView:
    return VisitsService(db).start_visit_for_queue_entry(
        access.context.doctor_user.id, queue_id
    )


@doctor_visits_router.get(
    "/{visit_id}",
    response_model=VisitDraftView,
    summary="Read a single draft or finalized visit (doctor-side)",
)
def read_visit_as_doctor(
    visit_id: Annotated[uuid.UUID, Path(...)],
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[
        CurrentPatientAccess | None,
        Depends(get_current_patient_access_for_doctor),
    ],
) -> VisitDraftView:
    if access is None:
        raise HealthLinkError(
            "No current chamber patient for the verified doctor.",
            status_code=404,
        )
    return VisitsService(db).read_visit_for_doctor(
        access.context.appointment.doctor_role_registration_id,
        visit_id,
    )


@doctor_visits_router.put(
    "/{visit_id}",
    response_model=VisitDraftView,
    summary="Update the clinical notes / diagnosis / follow-up for a DRAFT visit",
)
def update_visit(
    visit_id: Annotated[uuid.UUID, Path(...)],
    payload: VisitDraftUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[
        CurrentPatientAccess | None,
        Depends(get_current_patient_access_for_doctor),
    ],
) -> VisitDraftView:
    if access is None:
        raise HealthLinkError(
            "No current chamber patient for the verified doctor.",
            status_code=404,
        )
    return VisitsService(db).update_visit(
        visit_id=visit_id,
        payload=payload,
        acting_registration_id=access.context.appointment.doctor_role_registration_id,
    )


@citizen_visits_router.get(
    "/today",
    response_model=CitizenVisitListResponse,
    summary="List the authenticated citizen's visits scheduled today",
)
def list_my_visits_today(
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
) -> CitizenVisitListResponse:
    # `MedicalVisit.visit_date` is server-defaulted to UTC `now()`, so the
    # "today" filter must compare against the UTC calendar date rather
    # than the local `date.today()` to stay timezone-stable across the
    # test runner and the deployment environment.
    return CitizenVisitListResponse(
        visits=VisitsService(db).list_citizen_visits(
            context.profile.id,
            target_date=datetime.now(tz=timezone.utc).date(),
        )
    )


@citizen_visits_router.get(
    "/{visit_id}",
    response_model=VisitDraftView,
    summary="Read a single visit owned by the authenticated citizen",
)
def read_my_visit(
    visit_id: Annotated[uuid.UUID, Path(...)],
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
) -> VisitDraftView:
    return VisitsService(db).read_visit_for_citizen(
        context.profile.id, visit_id
    )


__all__ = ["doctor_visits_router", "citizen_visits_router"]
