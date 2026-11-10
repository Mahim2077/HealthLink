from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.diagnostics.session_models import LabSessionStatus


class CloseReason(StrEnum):
    EQUIPMENT = "EQUIPMENT"
    STAFF = "STAFF"
    SPECIMEN = "SPECIMEN"
    OTHER = "OTHER"


class CreateLabSession(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    catalog_code: str = Field(min_length=1, max_length=40)


class AcceptLabSession(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=22, max_length=32)
    attendance_deadline: AwareDatetime


class CloseLabSession(BaseModel):
    reason: CloseReason


class LabStep(BaseModel):
    tested_at: AwareDatetime | None = None


class PdfVersion(BaseModel):
    version: int = Field(ge=1)


class LabSessionView(BaseModel):
    id: UUID
    catalog_code: str
    test_name: str
    status: LabSessionStatus
    created_at: datetime
    attendance_deadline: datetime | None
    facility_name: str | None
    closed_reason: CloseReason | None
    share_code: str | None = None
    patient_name: str | None = None
    report_version: int | None = None
    report_test_name: str | None = None
    draft_version: int | None = None
    draft_test_name: str | None = None
    draft_tested_at: datetime | None = None
