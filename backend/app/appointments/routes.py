from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.appointments.dependencies import (
    get_current_citizen_for_booking,
    get_current_verified_doctor_for_chamber,
)
from app.appointments.schemas import (
    AppointmentBookingRequest,
    AppointmentBookingResponse,
    AppointmentListResponse,
    ChamberQueueActionResponse,
    ChamberSessionFinishResponse,
    ChamberSessionStartRequest,
    ChamberSessionView,
)
from app.appointments.service import AppointmentService
from app.citizens.dependencies import CitizenContext
from app.core.config import Settings
from app.db.session import get_db
from app.professionals.dependencies import ProfessionalAuthContext


appointments_router = APIRouter(
    prefix="/citizens/appointments",
    tags=["citizen-appointments"],
)
chamber_router = APIRouter(
    prefix="/professionals/chamber",
    tags=["doctor-chamber"],
)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@appointments_router.post(
    "",
    response_model=AppointmentBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment against a verified doctor",
)
def book_appointment(
    payload: AppointmentBookingRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen_for_booking)],
) -> AppointmentBookingResponse:
    return AppointmentService(
        db, _settings(request)
    ).book_appointment(context.auth.user.id, payload)


@appointments_router.get(
    "",
    response_model=AppointmentListResponse,
    summary="List the current citizen's appointments",
)
def list_my_appointments(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[CitizenContext, Depends(get_current_citizen_for_booking)],
) -> AppointmentListResponse:
    return AppointmentService(
        db, _settings(request)
    ).list_my_appointments(context.auth.user.id)


# ---------------------------------------------------------------------------
# Phase 11 — doctor chamber session + serial queue
# ---------------------------------------------------------------------------


@chamber_router.post(
    "/sessions/start",
    response_model=ChamberSessionView,
    status_code=status.HTTP_200_OK,
    summary="Start today's chamber session and call the lowest serial",
)
def start_chamber_session(
    payload: ChamberSessionStartRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
) -> ChamberSessionView:
    return AppointmentService(
        db, _settings(request)
    ).start_session(
        context,
        facility_id=payload.facility_id,
        session_date=payload.session_date,
    )


@chamber_router.get(
    "/sessions/today",
    response_model=ChamberSessionView | None,
    summary="View today's chamber session (current + waiting + finished)",
)
def view_today_chamber(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    facility_id: Annotated[uuid.UUID, Query(...)],
    session_date: Annotated[date | None, Query()] = None,
) -> ChamberSessionView | None:
    from datetime import date as _date

    target = session_date or _date.today()
    return AppointmentService(
        db, _settings(request)
    ).view_today_queue(
        context,
        facility_id=facility_id,
        session_date=target,
    )


@chamber_router.post(
    "/queue/call-next",
    response_model=ChamberQueueActionResponse,
    summary="Promote the lowest WAITING serial into the chamber",
)
def call_next_patient(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    facility_id: Annotated[uuid.UUID, Query(...)],
    session_date: Annotated[date | None, Query()] = None,
) -> ChamberQueueActionResponse:
    from datetime import date as _date

    target = session_date or _date.today()
    return AppointmentService(
        db, _settings(request)
    ).call_next(
        context,
        facility_id=facility_id,
        session_date=target,
    )


@chamber_router.post(
    "/queue/{queue_id}/complete",
    response_model=ChamberQueueActionResponse,
    summary="Complete the CURRENT chamber patient and advance the queue",
)
def complete_current_patient(
    queue_id: uuid.UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
) -> ChamberQueueActionResponse:
    return AppointmentService(
        db, _settings(request)
    ).complete_current(context, queue_id)


@chamber_router.post(
    "/queue/{queue_id}/skip",
    response_model=ChamberQueueActionResponse,
    summary="Skip the CURRENT patient and advance the queue",
)
def skip_current_patient(
    queue_id: uuid.UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
) -> ChamberQueueActionResponse:
    return AppointmentService(
        db, _settings(request)
    ).skip_current(context, queue_id)


@chamber_router.post(
    "/queue/{queue_id}/remove",
    response_model=ChamberQueueActionResponse,
    summary="Remove a patient from the chamber queue",
)
def remove_queue_entry(
    queue_id: uuid.UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
) -> ChamberQueueActionResponse:
    return AppointmentService(
        db, _settings(request)
    ).remove_entry(context, queue_id)


@chamber_router.post(
    "/queue/{queue_id}/no-show",
    response_model=ChamberQueueActionResponse,
    summary="Mark the CURRENT patient as no-show and advance the queue",
)
def mark_no_show(
    queue_id: uuid.UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
) -> ChamberQueueActionResponse:
    return AppointmentService(
        db, _settings(request)
    ).mark_no_show(context, queue_id)


@chamber_router.post(
    "/sessions/finish",
    response_model=ChamberSessionFinishResponse,
    summary="Close the doctor's chamber session for the day",
)
def finish_chamber_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    facility_id: Annotated[uuid.UUID, Query(...)],
    session_date: Annotated[date | None, Query()] = None,
) -> ChamberSessionFinishResponse:
    from datetime import date as _date

    target = session_date or _date.today()
    return AppointmentService(
        db, _settings(request)
    ).finish_session(
        context,
        facility_id=facility_id,
        session_date=target,
    )


__all__ = ["appointments_router", "chamber_router"]
