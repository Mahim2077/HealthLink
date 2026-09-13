import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmergencyProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    allergies: str | None = Field(default=None, max_length=4000)
    chronic_conditions: str | None = Field(default=None, max_length=4000)
    current_medications: str | None = Field(default=None, max_length=4000)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=32)
    special_notes: str | None = Field(default=None, max_length=4000)

    @field_validator("*", mode="before")
    @classmethod
    def normalize_blank(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class EmergencyProfileView(EmergencyProfileInput):
    citizen_id: uuid.UUID
    blood_group: str | None
    updated_at: datetime | None
