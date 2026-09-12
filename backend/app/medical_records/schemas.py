from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MedicalHistoryResourceType(StrEnum):
    VISIT = "VISIT"
    PRESCRIPTION = "PRESCRIPTION"


class MedicalHistoryQuery(BaseModel):
    resource_type: MedicalHistoryResourceType | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=20, ge=1, le=50)

class MedicalHistoryEvent(BaseModel):
    id: str
    resource_type: MedicalHistoryResourceType
    resource_id: uuid.UUID
    occurred_at: datetime
    title: str
    subtitle: str | None
    facility: str | None
    professional: str | None
    status: str
    summary: str | None
    appointment_id: uuid.UUID | None
    serial_number: int | None


class MedicalHistoryPage(BaseModel):
    items: list[MedicalHistoryEvent]
    page: int
    page_size: int
    total: int
    has_next: bool


__all__ = [
    "MedicalHistoryEvent",
    "MedicalHistoryPage",
    "MedicalHistoryQuery",
    "MedicalHistoryResourceType",
]
