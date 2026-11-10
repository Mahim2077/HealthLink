from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabSessionStatus(StrEnum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    CHECKED_IN = "CHECKED_IN"
    COLLECTED = "COLLECTED"
    PERFORMED = "PERFORMED"
    PUBLISHED = "PUBLISHED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    UNABLE = "UNABLE"


class LabSession(Base):
    __tablename__ = "diagnostic_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('REQUESTED','ACCEPTED','CHECKED_IN','COLLECTED','PERFORMED','PUBLISHED','EXPIRED','CANCELLED','UNABLE')", name="status"),
        Index("ix_diagnostic_sessions_citizen_created", "citizen_id", "created_at"),
        Index("ix_diagnostic_sessions_technician_created", "technician_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    citizen_id: Mapped[UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="RESTRICT"))
    technician_id: Mapped[UUID | None] = mapped_column(ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"))
    facility_id: Mapped[UUID | None] = mapped_column(ForeignKey("healthcare_facilities.id", ondelete="RESTRICT"))
    catalog_code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default=LabSessionStatus.REQUESTED)
    share_code: Mapped[str | None] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    attendance_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_reason: Mapped[str | None] = mapped_column(String(40))
    current_report_version: Mapped[int | None]


class DiagnosticPdf(Base):
    __tablename__ = "diagnostic_session_pdfs"
    __table_args__ = (Index("ix_diagnostic_session_pdfs_catalog_time", "catalog_code", "tested_at"),)

    session_id: Mapped[UUID] = mapped_column(ForeignKey("diagnostic_sessions.id", ondelete="RESTRICT"), primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    catalog_code: Mapped[str] = mapped_column(String(40))
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sha256: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
