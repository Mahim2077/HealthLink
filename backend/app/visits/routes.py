"""Consultations: centralized scoped reads, author-only clinical mutations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.auth.dependencies import AuthContext, get_current_auth_context
from app.access.policy import ClinicalReadPolicy
from app.clinical_audit.service import AuditService
from app.visits.models import MedicalVisit
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
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[
        CurrentPatientAccess | None,
        Depends(get_current_patient_access_for_doctor),
    ],
) -> DoctorCurrentPatientView | None:
    if access is None:
        return None
    decision = ClinicalReadPolicy(db).authorize(auth, access.context.citizen.id, "MEDICAL_HISTORY")
    result = _current_patient_view(
        access.context, access_source=access.source
    )
    AuditService(db).record(auth=auth, citizen_id=access.context.citizen.id, resource_type="MEDICAL_HISTORY", access_source=decision.source)
    return result


@doctor_visits_router.post(
    "/start-for-current/{queue_id}",
    response_model=VisitDraftView,
    status_code=status.HTTP_200_OK,
    summary="Open (or re-open) the draft visit for the given CURRENT chamber queue row",
)
def start_visit_for_current(
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    queue_id: Annotated[uuid.UUID, Path(...)],
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[
        CurrentPatientAccess,
        Depends(get_current_patient_access_for_queue_entry),
    ],
) -> VisitDraftView:
    AuditService(db).record(auth=auth, citizen_id=access.context.citizen.id, resource_type="VISIT", action="OPEN", commit=False)
    result = VisitsService(db).start_visit_for_queue_entry(
        access.context.doctor_user.id, queue_id
    )
    db.commit()  # Reopening an existing visit still persists the OPEN audit event.
    return result


@doctor_visits_router.get(
    "/{visit_id}",
    response_model=VisitDraftView,
    summary="Read a single draft or finalized visit (doctor-side)",
)
def read_visit_as_doctor(
    visit_id: Annotated[uuid.UUID, Path(...)],
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> VisitDraftView:
    ClinicalReadPolicy(db).doctor(auth)
    visit = db.get(MedicalVisit, visit_id)
    if visit is None:
        raise HealthLinkError("Visit not found.", status_code=404)
    decision = ClinicalReadPolicy(db).authorize(auth, visit.citizen_id, "VISIT", resource_id=visit.id, author_role_id=visit.doctor_role_registration_id, finalized=visit.status == "FINALIZED")
    result = VisitsService(db).read_visit_for_citizen(visit.citizen_id, visit_id)
    AuditService(db).record(auth=auth, citizen_id=visit.citizen_id, resource_type="VISIT", resource_id=visit.id, access_source=decision.source)
    return result


@doctor_visits_router.put(
    "/{visit_id}",
    response_model=VisitDraftView,
    summary="Update the clinical notes / diagnosis / follow-up for a DRAFT visit",
)
def update_visit(
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
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
    visit = db.get(MedicalVisit, visit_id)
    if visit and visit.doctor_role_registration_id == access.context.appointment.doctor_role_registration_id:
        AuditService(db).record(auth=auth, citizen_id=visit.citizen_id, resource_type="VISIT", resource_id=visit.id, action="UPDATE", commit=False)
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
