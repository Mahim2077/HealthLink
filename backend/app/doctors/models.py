from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PracticeWeekday(StrEnum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class PracticeScheduleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DoctorPracticeSchedule(Base):
    """Per-doctor weekly availability window bound to a healthcare facility.

    Used by the citizen doctor discovery flow (V6 section 13) and the doctor's
    own practice-schedule management endpoints (V6 section 14).
    """

    __tablename__ = "doctor_practice_schedules"
    __table_args__ = (
        CheckConstraint(
            "weekday IN ('MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY')",
            name="valid_weekday",
        ),
        CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')",
            name="valid_status",
        ),
        CheckConstraint(
            "max_patients >= 1",
            name="max_patients_positive",
        ),
        CheckConstraint(
            "end_time > start_time",
            name="end_after_start",
        ),
        Index(
            "ix_doctor_practice_schedules_doctor_user_id_facility_id_weekday",
            "doctor_user_id",
            "facility_id",
            "weekday",
        ),
        Index(
            "ix_doctor_practice_schedules_doctor_user_id",
            "doctor_user_id",
        ),
        Index(
            "ix_doctor_practice_schedules_facility_id",
            "facility_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    doctor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("healthcare_facilities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    weekday: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time = mapped_column(Time, nullable=False)
    end_time = mapped_column(Time, nullable=False)
    max_patients: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PracticeScheduleStatus.ACTIVE.value,
        server_default=PracticeScheduleStatus.ACTIVE.value,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    facility: Mapped["HealthcareFacility"] = relationship(  # noqa: F821
        "HealthcareFacility",
        foreign_keys=[facility_id],
        lazy="raise",
    )
