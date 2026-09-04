from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.visits.models import VisitStatus


class PatientSummary(BaseModel):
    """Compact patient view returned to a doctor for Phase 12."""

    model_config = ConfigDict(from_attributes=True)

    citizen_id: uuid.UUID
    full_name: str
    date_of_birth: str | None = None
    gender: str | None = None
    blood_group: str | None = None
    age_years: int | None = None


class VisitDraftView(BaseModel):
    """Consultation workspace view for the doctor.

    Phase 12 only exposes the visit body and the patient summary;
    emergency data is a placeholder per V6 prompt section scope
    discipline, and prescription/lab fields are Phase 13/14.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    citizen_id: uuid.UUID
    doctor_role_registration_id: uuid.UUID
    facility_id: uuid.UUID
    appointment_id: uuid.UUID | None
    prescription_id: uuid.UUID | None = None
    visit_date: datetime
    chief_complaint: str | None
    clinical_notes: str | None
    diagnosis: str | None
    follow_up_instructions: str | None
    status: VisitStatus
    finalized_at: datetime | None
    updated_at: datetime
    patient: PatientSummary | None = None
    access_source: str = Field(
        default="queue",
        description=(
            "Why the doctor may view this visit: ``queue`` (current"
            " chamber patient) or ``grant`` (manual patient grant)."
        ),
    )


class StartVisitForCurrentRequest(BaseModel):
    """Doctor opens a draft visit against the CURRENT queue entry."""

    model_config = ConfigDict(extra="forbid")

    queue_id: uuid.UUID


class VisitDraftUpdateRequest(BaseModel):
    """Doctor edits the consultation draft body."""

    model_config = ConfigDict(extra="forbid")

    chief_complaint: str | None = Field(default=None, max_length=4000)
    clinical_notes: str | None = Field(default=None, max_length=8000)
    diagnosis: str | None = Field(default=None, max_length=4000)
    follow_up_instructions: str | None = Field(default=None, max_length=4000)


class CitizenVisitSummary(BaseModel):
    """Compact view returned to the citizen for their today/own visits."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_user_id: uuid.UUID
    doctor_name: str
    facility_id: uuid.UUID
    facility_name: str
    appointment_id: uuid.UUID | None
    prescription_id: uuid.UUID | None = None
    serial_number: int | None
    visit_date: datetime
    status: VisitStatus
    finalized_at: datetime | None
    chief_complaint: str | None
    diagnosis: str | None
    follow_up_instructions: str | None


class CitizenVisitListResponse(BaseModel):
    visits: list[CitizenVisitSummary]


class DoctorCurrentPatientView(BaseModel):
    """Returned by the doctor "current patient" lookup used by the
    consultation workspace page so it can show the patient banner
    even before a draft visit exists."""

    model_config = ConfigDict(from_attributes=True)

    queue_id: uuid.UUID
    appointment_id: uuid.UUID
    serial_number: int
    citizen_id: uuid.UUID
    facility_id: uuid.UUID
    facility_name: str
    patient: PatientSummary
    visit: VisitDraftView | None = None


__all__ = [
    "CitizenVisitListResponse",
    "CitizenVisitSummary",
    "DoctorCurrentPatientView",
    "PatientSummary",
    "StartVisitForCurrentRequest",
    "VisitDraftUpdateRequest",
    "VisitDraftView",
]
