from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.facilities.schemas import FacilityResponse
from app.professionals.constants import (
    DoctorSpecialization,
    ProfessionalRoleCode,
    VerificationStatus,
)


class ProfessionalRegistrationSummary(BaseModel):
    id: uuid.UUID
    professional_id: uuid.UUID
    user_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    role_code: ProfessionalRoleCode
    role_name: str
    facility_name_submitted: str
    designation: str
    verification_status: VerificationStatus
    submitted_at: datetime


class ProfessionalRegistrationDetail(ProfessionalRegistrationSummary):
    additional_info: str | None
    bmdc_registration_number: str | None
    specialization: DoctorSpecialization | None
    qualification: str | None
    facility: FacilityResponse | None
    verified_at: datetime | None
    verified_by: uuid.UUID | None
    rejected_at: datetime | None
    rejection_reason: str | None


class VerifyProfessionalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facility_id: uuid.UUID
    specialization: DoctorSpecialization | None = None
    qualification: Annotated[str | None, Field(max_length=255)] = None

    @field_validator("qualification", mode="before")
    @classmethod
    def strip_qualification(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class RejectProfessionalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Annotated[str, Field(min_length=1)]

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value
