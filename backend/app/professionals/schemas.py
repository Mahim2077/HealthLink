from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator, model_validator

from app.professionals.constants import ProfessionalRoleCode, VerificationStatus


ProfessionalPassword = Annotated[SecretStr, Field(min_length=8, max_length=128)]


class ProfessionalApplicationFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_code: ProfessionalRoleCode
    facility_name: Annotated[str, Field(min_length=1, max_length=255)]
    designation: Annotated[str, Field(min_length=1, max_length=150)]
    additional_info: Annotated[str, Field(min_length=1)]
    bmdc_registration_number: Annotated[str | None, Field(max_length=100)] = None

    @field_validator(
        "facility_name",
        "designation",
        "additional_info",
        "bmdc_registration_number",
        mode="before",
    )
    @classmethod
    def strip_application_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def validate_role_specific_fields(self) -> ProfessionalApplicationFields:
        if (
            self.role_code is ProfessionalRoleCode.DOCTOR
            and self.bmdc_registration_number is None
        ):
            raise ValueError("BM&DC Registration Number is required for doctors.")
        if (
            self.role_code is not ProfessionalRoleCode.DOCTOR
            and self.bmdc_registration_number is not None
        ):
            raise ValueError("BM&DC Registration Number applies only to doctors.")
        return self


class ProfessionalRegistrationRequest(ProfessionalApplicationFields):
    email: EmailStr
    password: ProfessionalPassword
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    nid_number: Annotated[str, Field(min_length=1, max_length=32)]

    @field_validator("first_name", "last_name", "nid_number", mode="before")
    @classmethod
    def strip_account_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ProfessionalOnboardingRequest(ProfessionalApplicationFields):
    pass


class ProfessionalApplicationResponse(BaseModel):
    user_id: uuid.UUID
    professional_id: uuid.UUID
    role_registration_id: uuid.UUID
    role_code: ProfessionalRoleCode
    verification_status: VerificationStatus
    submitted_at: datetime
