from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AppointmentStatus(StrEnum):
    """Appointment lifecycle values per V6 section 15."""

    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    REMOVED_BY_DOCTOR = "REMOVED_BY_DOCTOR"
    NO_SHOW = "NO_SHOW"


class QueueStatus(StrEnum):
    """Chamber queue entry lifecycle per V6 section 19."""

    WAITING = "WAITING"
    CURRENT = "CURRENT"
    SKIPPED = "SKIPPED"
    DONE = "DONE"
    REMOVED = "REMOVED"
    CANCELLED = "CANCELLED"


class SessionStatus(StrEnum):
    """Daily chamber session lifecycle per V6 section 18."""

    NOT_STARTED = "NOT_STARTED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class DoctorPracticeSession(Base):
    """One day's chamber session for a doctor at a single facility.

    Acts as the queue container created lazily when the first appointment
    is booked for the date or explicitly when the doctor starts practice.
    """

    __tablename__ = "doctor_practice_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('NOT_STARTED','ACTIVE','COMPLETED')",
            name="valid_status",
        ),
        UniqueConstraint(
            "doctor_role_registration_id",
            "facility_id",
            "session_date",
            name="uq_doctor_practice_sessions_doctor_role_reg_facility_date",
        ),
        Index(
            "ix_doctor_practice_sessions_doctor_role_registration_id",
            "doctor_role_registration_id",
        ),
        Index(
            "ix_doctor_practice_sessions_facility_id",
            "facility_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    doctor_role_registration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("healthcare_facilities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SessionStatus.NOT_STARTED.value,
        server_default=SessionStatus.NOT_STARTED.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
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


class Appointment(Base):
    """A citizen's booked serial slot for one date at a doctor's chamber.

    Serial numbers are computed by the booking service as ``MAX(existing
    serial) + 1`` per (doctor_role_registration_id, facility_id,
    appointment_date). Database unique constraint enforces the
    invariant in V6 section 16; advisory locks make it concurrent-safe.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('BOOKED','CANCELLED','COMPLETED',"
            "'REMOVED_BY_DOCTOR','NO_SHOW')",
            name="valid_status",
        ),
        CheckConstraint(
            "serial_number >= 1",
            name="serial_number_positive",
        ),
        UniqueConstraint(
            "doctor_role_registration_id",
            "facility_id",
            "appointment_date",
            "serial_number",
            name="uq_appointments_doctor_role_reg_facility_date_serial",
        ),
        Index(
            "ix_appointments_doctor_role_registration_id",
            "doctor_role_registration_id",
        ),
        Index("ix_appointments_citizen_id", "citizen_id"),
        Index("ix_appointments_facility_id", "facility_id"),
        Index("ix_appointments_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("citizen_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_role_registration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("healthcare_facilities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    serial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    booked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
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


class AppointmentQueueEntry(Base):
    """Chamber queue row for one appointment.

    The serial number is owned by the parent ``appointments`` row and is
    read by joining; this table only tracks the queue lifecycle,
    ``became_current_at`` audit timestamp, and removal bookkeeping.

    A single CURRENT row per ``practice_session_id`` is enforced in
    PostgreSQL by a partial unique index created in migration 0018.
    """

    __tablename__ = "appointment_queue_entries"
    __table_args__ = (
        CheckConstraint(
            "queue_status IN ('WAITING','CURRENT','SKIPPED','DONE',"
            "'REMOVED','CANCELLED')",
            name="valid_status",
        ),
        UniqueConstraint(
            "appointment_id",
            name="uq_appointment_queue_entries_appointment_id",
        ),
        Index(
            "ix_appointment_queue_entries_practice_session_id",
            "practice_session_id",
        ),
        Index(
            "ix_appointment_queue_entries_queue_status",
            "queue_status",
        ),
        Index(
            "uq_one_current_queue_entry_per_session",
            "practice_session_id",
            unique=True,
            postgresql_where=text("queue_status = 'CURRENT'"),
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    practice_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctor_practice_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    queue_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=QueueStatus.WAITING.value,
        server_default=QueueStatus.WAITING.value,
    )
    became_current_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(
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
