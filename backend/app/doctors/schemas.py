from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Annotated

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.doctors.models import PracticeScheduleStatus, PracticeWeekday


class DoctorSearchFilters(BaseModel):
    """Citizen-side filters for ``GET /api/v1/doctors``.

    At least one filter must be provided, mirroring the V6 doctor search model.
    ``nid_number`` is explicitly excluded: NIDs must never be searchable.
    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str | None, Field(max_length=200)] = None
    facility_name: Annotated[str | None, Field(max_length=200)] = None
    weekday: PracticeWeekday | None = None
    limit: Annotated[int, Field(ge=1, le=50)] = 20

    @field_validator("name", "facility_name", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    def has_filter(self) -> bool:
        return any(
            value is not None
            for value in (self.name, self.facility_name, self.weekday)
        )

    @classmethod
    def as_query(cls, request: Request) -> "DoctorSearchFilters":
        params = {
            key: value
            for key, value in request.query_params.multi_items()
            if key in cls.model_fields
        }
        try:
            return cls(**params)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc


class PracticeDay(BaseModel):
    """One weekly window a doctor keeps for practice.

    Times use ``HH:MM`` strings so they remain timezone-neutral in JSON.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    facility_name: str
    weekday: PracticeWeekday
    start_time: time
    end_time: time
    max_patients: int
    status: PracticeScheduleStatus


class DoctorSummary(BaseModel):
    """Compact doctor entry returned by ``GET /api/v1/doctors``.

    Deliberately omits ``nid_number``, ``bmdc_registration_number`` and any
    other PII: citizens only see name + facility + specialization + verified
    flag, per V6 section 13.
    """

    id: uuid.UUID
    name: str
    first_name: str
    last_name: str
    facility_id: uuid.UUID
    facility_name: str
    facility_type: str
    designation: str
    role_code: str
    verified: bool
    specialization: str | None = None


class DoctorProfile(DoctorSummary):
    """Full doctor profile surfaced by ``GET /api/v1/doctors/{id}``.

    Inherits everything from :class:`DoctorSummary` (already PII-safe) and
    adds practice days. ``bmdc_number`` and ``nid_number`` are deliberately
    absent — they are sensitive identifiers that the citizen-facing surface
    must never leak.
    """

    email: str
    verified_at: datetime | None = None
    submitted_at: datetime
    practice_days: list[PracticeDay] = Field(default_factory=list)


class PracticeScheduleEntry(BaseModel):
    """Doctor-facing representation of one schedule row from
    ``/professionals/me/practice-schedule*``.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    facility_id: uuid.UUID
    facility_name: str
    weekday: PracticeWeekday
    start_time: time
    end_time: time
    max_patients: int
    status: PracticeScheduleStatus
    created_at: datetime
    updated_at: datetime


class PracticeScheduleWriteRequest(BaseModel):
    """Shared payload for create + update on the doctor's own schedule."""

    model_config = ConfigDict(extra="forbid")

    facility_id: uuid.UUID
    weekday: PracticeWeekday
    start_time: time
    end_time: time
    max_patients: Annotated[int, Field(ge=1, le=200)]
    status: PracticeScheduleStatus = PracticeScheduleStatus.ACTIVE

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def coerce_time(cls, value: object) -> object:
        if isinstance(value, str) and len(value) == 5 and value[2] == ":":
            return value + ":00"
        return value

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time: time, info) -> time:
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class PracticeScheduleCreateResponse(BaseModel):
    schedule: PracticeScheduleEntry


class PracticeScheduleDeleteResponse(BaseModel):
    id: uuid.UUID
    deleted_at: datetime


class _UnavailableBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DoctorScheduleUnavailableResponse(BaseModel):
    reason: str
    next_action: str


__all__ = [
    "DoctorSearchFilters",
    "DoctorSummary",
    "DoctorProfile",
    "PracticeDay",
    "PracticeScheduleEntry",
    "PracticeScheduleWriteRequest",
    "PracticeScheduleCreateResponse",
    "PracticeScheduleDeleteResponse",
]
