from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VisitStatus(StrEnum):
    """Medical visit lifecycle for V6 section 25.

    ``DRAFT`` covers the active chamber consultation; ``FINALIZED``
    is the terminal state set when Phase 14 finishes the appointment.
    """

    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class PatientAccessScope(StrEnum):
    """Allowed values for ``patient_access_grants.access_scope``.

    V6 section 24 leaves the explicit values for the premium
    manual-grant feature, so Phase 12 ships a conservative pair:
    ``FULL_RECORD`` and ``LIMITED``. Both grant the doctor full
    read access to the citizen's Phase 12 workspace because manual
    grants are the documented alternative to the current-queue
    relationship; Phase 14+ can narrow this.
    """

    FULL_RECORD = "FULL_RECORD"
    LIMITED = "LIMITED"


class PatientAccessGrant(Base):
    """Manual citizen-to-professional access grant (V6 section 24).

    Phase 12 only stores the table so the access dependency can
    recognise a valid pre-existing grant when present; no Phase 12
    route exposes CRUD against it.
    """

    __tablename__ = "patient_access_grants"
    __table_args__ = (
        CheckConstraint(
            "access_scope IN ('FULL_RECORD','LIMITED')",
            name="valid_scope",
        ),
        Index("ix_patient_access_grants_citizen_id", "citizen_id"),
        Index(
            "ix_patient_access_grants_professional_role_registration_id",
            "professional_role_registration_id",
        ),
        Index(
            "ix_patient_access_grants_active",
            "citizen_id",
            "professional_role_registration_id",
            postgresql_where=text("revoked_at IS NULL"),
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("citizen_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    professional_role_registration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    access_scope: Mapped[str] = mapped_column(
        String(length=50),
        nullable=False,
        default=PatientAccessScope.FULL_RECORD.value,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class MedicalVisit(Base):
    """Structured chamber consultation record (V6 section 25).

    The visit is created in ``DRAFT`` while the doctor is consulting
    and finalised when the appointment finishes. ``appointment_id`` is
    UNIQUE so the "at most one visit per appointment" invariant holds
    at the database layer.
    """

    __tablename__ = "medical_visits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','FINALIZED')",
            name="valid_status",
        ),
        UniqueConstraint(
            "appointment_id", name="uq_medical_visits_appointment_id"
        ),
        Index("ix_medical_visits_citizen_id", "citizen_id"),
        Index(
            "ix_medical_visits_doctor_role_registration_id",
            "doctor_role_registration_id",
        ),
        Index("ix_medical_visits_facility_id", "facility_id"),
        Index(
            "ix_medical_visits_draft",
            "citizen_id",
            "doctor_role_registration_id",
            postgresql_where=text("status = 'DRAFT'"),
        ).ddl_if(dialect="postgresql"),
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
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    visit_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(length=32),
        nullable=False,
        default=VisitStatus.DRAFT.value,
        server_default=VisitStatus.DRAFT.value,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    appointment: Mapped["Appointment | None"] = relationship(  # noqa: F821
        "Appointment", foreign_keys=[appointment_id], lazy="select"
    )
    prescription: Mapped["Prescription | None"] = relationship(  # noqa: F821
        "Prescription", back_populates="visit", uselist=False, lazy="select"
    )


__all__ = [
    "MedicalVisit",
    "PatientAccessGrant",
    "PatientAccessScope",
    "VisitStatus",
]
