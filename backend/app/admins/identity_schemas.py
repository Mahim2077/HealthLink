from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, field_validator

from app.citizens.constants import CitizenRegistrationMethod


class CitizenIdentitySearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nid_number: Annotated[str | None, Field(max_length=32)] = None
    birth_certificate_number: Annotated[str | None, Field(max_length=64)] = None
    email: EmailStr | None = None
    user_id: uuid.UUID | None = None
    limit: Annotated[int, Field(ge=1, le=50)] = 20

    @field_validator("nid_number", "birth_certificate_number", mode="before")
    @classmethod
    def strip_identity(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    def has_filter(self) -> bool:
        return any(
            value is not None
            for value in (
                self.nid_number,
                self.birth_certificate_number,
                self.email,
                self.user_id,
            )
        )

    @classmethod
    def as_query(cls, request: Request) -> "CitizenIdentitySearchQuery":
        """FastAPI dependency that parses the query string into this schema.

        Surfacing validation errors from this dependency as
        ``RequestValidationError`` lets FastAPI emit a 422 response (matching
        the rest of the API) instead of a 500.
        """
        params = {
            key: value
            for key, value in request.query_params.multi_items()
            if key in cls.model_fields
        }
        try:
            return cls(**params)
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc


class CitizenIdentitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    registered_with: CitizenRegistrationMethod
    nid_number: str | None
    birth_certificate_number: str | None
    nid_added_at: datetime | None
    identity_created_at: datetime
    identity_updated_at: datetime


class CitizenIdentityDetail(CitizenIdentitySummary):
    national_identifier_id: uuid.UUID | None
    national_identifier_created_at: datetime | None
    date_of_birth: date | None
    gender: str | None
    blood_group: str | None
    address: str | None
    auth_session_count: int
    created_at: datetime
    updated_at: datetime


class CitizenIdentityCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correction_type: Literal["NID", "BCN"]
    new_value: Annotated[str, Field(min_length=1, max_length=64)]
    reason: Annotated[str, Field(min_length=1, max_length=2000)]

    @field_validator("new_value", "reason", mode="before")
    @classmethod
    def strip_value(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class CitizenIdentityCorrectionResponse(BaseModel):
    user_id: uuid.UUID
    correction_type: Literal["NID", "BCN"]
    previous_value: str | None
    new_value: str
    corrected_at: datetime
    audit_log_id: uuid.UUID