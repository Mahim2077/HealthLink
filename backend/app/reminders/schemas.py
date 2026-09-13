import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReminderInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    medicine: str = Field(min_length=1, max_length=200)
    prescription_item_id: uuid.UUID | None = None
    start_date: date
    end_date: date | None = None
    timezone: Literal["Asia/Dhaka"] = "Asia/Dhaka"
    is_active: bool = True
    times: list[time] = Field(min_length=1, max_length=24)

    @field_validator("times")
    @classmethod
    def valid_times(cls, values):
        if any(t.tzinfo or t.second or t.microsecond for t in values):
            raise ValueError("Use local daily times with minute precision.")
        if len(set(values)) != len(values):
            raise ValueError("Daily times must be unique.")
        return sorted(values)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date.")
        return self


class ReminderView(ReminderInput):
    id: uuid.UUID


class ActiveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


class NotificationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    message: str
    due_at: datetime
    read_at: datetime | None
    acknowledged_at: datetime | None


class PrescriptionChoice(BaseModel):
    id: uuid.UUID
    medicine: str
    dosage: str
    prescription_date: date
