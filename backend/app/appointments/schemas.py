from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.appointments.models import AppointmentStatus, QueueStatus, SessionStatus


class AppointmentBookingRequest(BaseModel):
    """Citizen-initiated appointment booking payload."""

    model_config = ConfigDict(extra="forbid")

    doctor_user_id: uuid.UUID
    facility_id: uuid.UUID
    appointment_date: date
    reason: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("appointment_date")
    @classmethod
    def appointment_date_not_in_past(cls, value: date) -> date:
        from datetime import date as _date

        if value < _date.today():
            raise ValueError("appointment_date cannot be in the past.")
        return value

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AppointmentQueueEntryView(BaseModel):
    """Minimal queue projection for a citizen appointment response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    queue_status: QueueStatus
    became_current_at: datetime | None
    finished_at: datetime | None
    removed_at: datetime | None


class AppointmentBookingResponse(BaseModel):
    """Response returned after a successful booking."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    citizen_id: uuid.UUID
    doctor_role_registration_id: uuid.UUID
    doctor_user_id: uuid.UUID
    facility_id: uuid.UUID
    facility_name: str
    appointment_date: date
    serial_number: int
    status: AppointmentStatus
    reason: str | None
    booked_at: datetime
    queue: AppointmentQueueEntryView


class AppointmentListEntry(BaseModel):
    """Compact appointment entry returned by the history listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_user_id: uuid.UUID
    doctor_name: str
    facility_id: uuid.UUID
    facility_name: str
    appointment_date: date
    serial_number: int
    status: AppointmentStatus
    booked_at: datetime
    cancelled_at: datetime | None
    completed_at: datetime | None


class AppointmentListResponse(BaseModel):
    appointments: list[AppointmentListEntry]


# ---------------------------------------------------------------------------
# Phase 11 — Chamber session and serial queue projections
# ---------------------------------------------------------------------------


class ChamberAppointmentView(BaseModel):
    """One queue row as the doctor sees it on the chamber dashboard."""

    model_config = ConfigDict(from_attributes=True)

    queue_id: uuid.UUID
    appointment_id: uuid.UUID
    serial_number: int
    status: AppointmentStatus
    queue_status: QueueStatus
    reason: str | None
    booked_at: datetime
    became_current_at: datetime | None
    finished_at: datetime | None
    removed_at: datetime | None


class ChamberSessionStartRequest(BaseModel):
    """Doctor opens today's chamber session for a given facility + date."""

    model_config = ConfigDict(extra="forbid")

    facility_id: uuid.UUID
    session_date: date

    @field_validator("session_date")
    @classmethod
    def session_date_not_in_past(cls, value: date) -> date:
        from datetime import date as _date

        if value < _date.today():
            raise ValueError("session_date cannot be in the past.")
        return value


class ChamberSessionView(BaseModel):
    """Current chamber session summary returned by `get today`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    facility_name: str
    session_date: date
    status: SessionStatus
    started_at: datetime | None
    ended_at: datetime | None
    current: ChamberAppointmentView | None
    waiting: list[ChamberAppointmentView]
    finished: list[ChamberAppointmentView]


class ChamberQueueActionResponse(BaseModel):
    """Result of any queue action (call-next, skip, remove, no-show, complete)."""

    model_config = ConfigDict(from_attributes=True)

    queue_id: uuid.UUID
    appointment_id: uuid.UUID
    serial_number: int
    queue_status: QueueStatus
    appointment_status: AppointmentStatus
    became_current_at: datetime | None
    finished_at: datetime | None
    removed_at: datetime | None
    # After the action, the next CURRENT row (if any) — populated for
    # call-next / skip / remove / no-show / complete that promote a
    # successor; absent when no WAITING rows remain.
    next_current: ChamberAppointmentView | None = None


class ChamberSessionFinishResponse(BaseModel):
    """Doctor closes an open chamber session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    session_date: date
    status: SessionStatus
    started_at: datetime | None
    ended_at: datetime | None
    remaining_waiting: int