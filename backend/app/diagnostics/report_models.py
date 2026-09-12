from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabReport(Base):
    __tablename__ = "lab_reports"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','FINALIZED')", name="valid_status"),
        CheckConstraint("(status = 'DRAFT' AND finalized_at IS NULL) OR (status = 'FINALIZED' AND finalized_at IS NOT NULL)", name="finalization_consistent"),
        Index("ix_lab_reports_citizen_date", "citizen_id", "report_date"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    diagnostic_test_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("diagnostic_tests.id", ondelete="RESTRICT"), unique=True)
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="RESTRICT"))
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("healthcare_facilities.id", ondelete="RESTRICT"))
    created_by_role_registration_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"))
    report_date: Mapped[date] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", server_default="DRAFT")
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LabReportItem(Base):
    __tablename__ = "lab_report_items"
    __table_args__ = (Index("ix_lab_report_items_report", "lab_report_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lab_report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lab_reports.id", ondelete="CASCADE"))
    parameter_name: Mapped[str] = mapped_column(String(150))
    result_value_text: Mapped[str] = mapped_column(String(500))
    result_value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(150))
    flag: Mapped[str | None] = mapped_column(String(50))
