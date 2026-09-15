from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.facilities.constants import FacilityType


class FacilityWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    facility_type: FacilityType
    registration_number: Annotated[str | None, Field(max_length=100)] = None
    address: Annotated[str, Field(min_length=1)]
    district_code: Annotated[str | None, Field(max_length=16)] = None
    upazila_code: Annotated[str | None, Field(max_length=20)] = None
    phone: Annotated[str | None, Field(max_length=32)] = None
    email: EmailStr | None = None
    is_active: bool = True

    @field_validator(
        "name",
        "registration_number",
        "address",
        "phone",
        "district_code",
        "upazila_code",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def validate_area_pair(self) -> "FacilityWriteRequest":
        if (self.district_code is None) != (self.upazila_code is None):
            raise ValueError("Select both a zila and an upazila.")
        return self


class FacilityResponse(BaseModel):
    id: uuid.UUID
    name: str
    facility_type: FacilityType
    registration_number: str | None
    address: str
    district_code: str | None
    upazila_code: str | None
    location_status: str
    location_matched_address: str | None
    location_confirmed_at: datetime | None
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FacilityLocationConfirmationResponse(BaseModel):
    facility: FacilityResponse
    message: str
