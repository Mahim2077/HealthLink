from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.diagnostics.models import DiagnosticTestStatus


class DiagnosticTestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visit_id: uuid.UUID
    test_name: Annotated[str, Field(min_length=1, max_length=255)]
    instructions: str | None = None
    assigned_to_role_registration_id: uuid.UUID | None = None

    @field_validator("test_name", "instructions", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class DiagnosticAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assigned_to_role_registration_id: uuid.UUID | None


class DiagnosticTestView(BaseModel):
    id: uuid.UUID
    citizen_id: uuid.UUID
    visit_id: uuid.UUID | None
    requested_by_role_registration_id: uuid.UUID
    assigned_to_role_registration_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    facility_name: str | None
    test_name: str
    instructions: str | None
    status: DiagnosticTestStatus
    requested_by_name: str
    assigned_to_name: str | None
    created_at: datetime
    updated_at: datetime


class DiagnosticTestListResponse(BaseModel):
    tests: list[DiagnosticTestView]


class DiagnosticTechnicianChoice(BaseModel):
    role_registration_id: uuid.UUID
    full_name: str
    designation: str
    facility_id: uuid.UUID
    facility_name: str
