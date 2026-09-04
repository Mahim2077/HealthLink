"""Phase 13 prescription Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PrescriptionItemPayload(BaseModel):
    """One medicine row as posted by the author doctor."""

    model_config = ConfigDict(extra="forbid")

    medicine_name: str = Field(min_length=1, max_length=200)
    dosage: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    duration: str = Field(min_length=1, max_length=100)
    instructions: str | None = Field(default=None, max_length=4000)

    @field_validator(
        "medicine_name",
        "dosage",
        "frequency",
        "duration",
        mode="before",
    )
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                raise ValueError("Medicine fields cannot be blank.")
            return normalized
        return value

    @field_validator("instructions", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class PrescriptionItemView(BaseModel):
    """Persisted medicine row."""

    id: uuid.UUID
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None


class PrescriptionCreateRequest(BaseModel):
    """Payload for ``POST /api/v1/visits/{visit_id}/prescription``."""

    model_config = ConfigDict(extra="forbid")

    items: list[PrescriptionItemPayload] = Field(min_length=1, max_length=50)
    diagnostic_information: str | None = Field(default=None, max_length=8000)
    medical_advice: str | None = Field(default=None, max_length=8000)
    notes: str | None = Field(default=None, max_length=8000)

    @field_validator(
        "diagnostic_information", "medical_advice", "notes", mode="before"
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class PrescriptionUpdateRequest(BaseModel):
    """Payload for ``PUT /api/v1/prescriptions/{id}``."""

    model_config = ConfigDict(extra="forbid")

    items: list[PrescriptionItemPayload] = Field(min_length=1, max_length=50)
    diagnostic_information: str | None = Field(default=None, max_length=8000)
    medical_advice: str | None = Field(default=None, max_length=8000)
    notes: str | None = Field(default=None, max_length=8000)

    @field_validator(
        "diagnostic_information", "medical_advice", "notes", mode="before"
    )
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class PrescriptionView(BaseModel):
    """Single prescription payload returned by the API."""

    id: uuid.UUID
    visit_id: uuid.UUID
    citizen_id: uuid.UUID
    author_doctor_role_registration_id: uuid.UUID
    diagnostic_information: str | None
    medical_advice: str | None
    notes: str | None
    items: list[PrescriptionItemView]
    pdf_available: bool
    pdf_file_name: str | None
    pdf_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime


__all__ = [
    "PrescriptionCreateRequest",
    "PrescriptionItemPayload",
    "PrescriptionItemView",
    "PrescriptionUpdateRequest",
    "PrescriptionView",
]
