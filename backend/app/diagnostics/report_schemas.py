import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LabItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    parameter_name: Annotated[str, Field(min_length=1, max_length=150)]
    result_value_text: Annotated[str, Field(min_length=1, max_length=500)]
    result_value_numeric: Annotated[Decimal | None, Field(max_digits=18, decimal_places=6, allow_inf_nan=False)] = None
    unit: Annotated[str | None, Field(max_length=50)] = None
    reference_range: Annotated[str | None, Field(max_length=150)] = None
    flag: Annotated[str | None, Field(max_length=50)] = None

    @field_validator("unit", "reference_range", "flag", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class LabReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    report_date: date
    summary: Annotated[str | None, Field(max_length=10000)] = None
    items: Annotated[list[LabItemInput], Field(min_length=1, max_length=100)]


class LabReportView(LabReportInput):
    id: uuid.UUID
    diagnostic_test_id: uuid.UUID
    citizen_id: uuid.UUID
    status: str
    finalized_at: datetime | None
    test_name: str
    facility_name: str | None


class LabTrendPoint(BaseModel):
    report_id: uuid.UUID
    report_date: date
    parameter_name: str
    value: Decimal
    unit: str | None
