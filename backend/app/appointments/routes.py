from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.appointments.dependencies import get_current_citizen_for_booking
from app.appointments.schemas import (
    AppointmentBookingRequest,
    AppointmentBookingResponse,
    AppointmentListResponse,
)
from app.appointments.service import AppointmentService
from app.citizens.dependencies import CitizenContext
from app.core.config import Settings
from app.db.session import get_db


appointments_router = APIRouter(
    prefix="/citizens/appointments",
    tags=["citizen-appointments"],
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


__all__ = ["appointments_router"]
