import uuid
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field


class UpcomingAppointment(BaseModel):
    id: uuid.UUID
    appointment_date: date
    facility_name: str
    serial_number: int


class RecentPrescription(BaseModel):
    id: uuid.UUID
    created_at: datetime


class RecentReport(BaseModel):
    diagnostic_test_id: uuid.UUID
    test_name: str
    report_date: date


class CitizenOverview(BaseModel):
    today: date
    upcoming_appointment: UpcomingAppointment | None
    recent_prescription: RecentPrescription | None
    latest_report: RecentReport | None
    active_reminders: int = Field(ge=0)
    unread_notifications: int = Field(ge=0)
    emergency_profile_updated_at: datetime | None


class ChamberOverview(BaseModel):
    facility_name: str
    status: str
    waiting_count: int = Field(ge=0)
    current_serial: int | None


class ProfessionalOverview(BaseModel):
    today: date
    role_code: Literal["DOCTOR", "LAB_TECHNICIAN"]
    chambers: list[ChamberOverview] = Field(default_factory=list, max_length=10)
    chambers_has_more: bool = False
    requested_tests: int = Field(ge=0)
    in_progress_tests: int = Field(ge=0)
    draft_reports: int = Field(ge=0)
    finalized_reports: int = Field(ge=0)
    recent_prescription: RecentPrescription | None = None


class AdminOverview(BaseModel):
    pending_professional_registrations: int = Field(ge=0)
    active_facilities: int = Field(ge=0)
    facilities_needing_location: int = Field(ge=0)
