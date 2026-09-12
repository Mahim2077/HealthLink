from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiagnosticTestStatus(StrEnum):
    REQUESTED = "REQUESTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('REQUESTED','IN_PROGRESS','COMPLETED','CANCELLED')",
            name="valid_status",
        ),
        Index("ix_diagnostic_tests_citizen_id", "citizen_id"),
        Index("ix_diagnostic_tests_requested_by", "requested_by_role_registration_id"),
        Index("ix_diagnostic_tests_assigned_to_status", "assigned_to_role_registration_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), nullable=False)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("medical_visits.id", ondelete="RESTRICT"))
    requested_by_role_registration_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"), nullable=False)
    assigned_to_role_registration_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"))
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("healthcare_facilities.id", ondelete="RESTRICT"))
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DiagnosticTestStatus.REQUESTED.value, server_default=DiagnosticTestStatus.REQUESTED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


__all__ = ["DiagnosticTest", "DiagnosticTestStatus"]
