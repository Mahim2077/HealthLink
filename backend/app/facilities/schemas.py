from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.facilities.constants import FacilityType


class FacilityWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=200)]
    facility_type: FacilityType
    registration_number: Annotated[str | None, Field(max_length=100)] = None
    address: Annotated[str, Field(min_length=1)]
    phone: Annotated[str | None, Field(max_length=32)] = None
    email: EmailStr | None = None
    is_active: bool = True

    @field_validator("name", "registration_number", "address", "phone", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class FacilityResponse(BaseModel):
    id: uuid.UUID
    name: str
    facility_type: FacilityType
    registration_number: str | None
    address: str
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
