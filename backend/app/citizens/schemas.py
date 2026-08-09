from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.citizens.constants import CitizenRegistrationMethod


RegistrationPassword = Annotated[SecretStr, Field(min_length=8, max_length=128)]
LoginPassword = Annotated[SecretStr, Field(min_length=1, max_length=128)]


class CitizenRegistrationRequest(BaseModel):
    email: EmailStr
    password: RegistrationPassword
    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    date_of_birth: date
    gender: Annotated[str, Field(min_length=1, max_length=32)]
    blood_group: Annotated[str | None, Field(max_length=8)] = None
    address: str | None = None
    nid_number: Annotated[str | None, Field(max_length=32)] = None
    birth_certificate_number: Annotated[str | None, Field(max_length=64)] = None

    @field_validator(
        "first_name",
        "last_name",
        "gender",
        "blood_group",
        "address",
        "nid_number",
        "birth_certificate_number",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def require_exactly_one_initial_identity(self) -> CitizenRegistrationRequest:
        has_nid = self.nid_number is not None
        has_bcn = self.birth_certificate_number is not None
        if has_nid == has_bcn:
            raise ValueError("Provide exactly one of NID or Birth Certificate Number.")
        return self

    @field_validator("date_of_birth")
    @classmethod
    def reject_future_date_of_birth(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class CitizenLoginRequest(BaseModel):
    email: EmailStr
    password: LoginPassword


class CitizenProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Annotated[str, Field(min_length=1, max_length=100)]
    last_name: Annotated[str, Field(min_length=1, max_length=100)]
    date_of_birth: date
    gender: Annotated[str, Field(min_length=1, max_length=32)]
    blood_group: Annotated[str | None, Field(max_length=8)] = None
    address: str | None = None

    @field_validator(
        "first_name",
        "last_name",
        "gender",
        "blood_group",
        "address",
        mode="before",
    )
    @classmethod
    def strip_profile_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("date_of_birth")
    @classmethod
    def reject_future_date_of_birth(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class CitizenAddNidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nid_number: Annotated[str, Field(min_length=1, max_length=32)]
    confirmation: Annotated[str, Field(min_length=1, max_length=32)]

    @field_validator("nid_number", mode="before")
    @classmethod
    def strip_nid_number(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class CitizenRegistrationResponse(BaseModel):
    user_id: uuid.UUID
    citizen_id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    registered_with: CitizenRegistrationMethod
    created_at: datetime


class CitizenProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    citizen_id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    blood_group: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime


class CitizenIdentityResponse(BaseModel):
    registered_with: CitizenRegistrationMethod
    nid_number: str | None
    birth_certificate_number: str | None
    nid_added_at: datetime | None
