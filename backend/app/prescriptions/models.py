"""Phase 13 prescription ORM models.

Three tables from V6 sections 26-28:

* ``prescriptions`` - header row, UNIQUE on ``visit_id`` so the
  "at most one prescription per visit" invariant holds at the database
  level. Authorised for edits by the author doctor (an intentional
  exception to ordinary finalized-record immutability; Phase 14 closes
  the window once the appointment is finished).
* ``prescription_items`` - structured medicines rows; ``CASCADE`` on
  delete so removing a prescription wipes its medicines.
* ``prescription_documents`` - pointer to the rendered PDF binary that
  lives in private storage; ``UNIQUE`` on ``prescription_id`` so each
  prescription has exactly one current document.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Prescription(Base):
    """Chamber prescription header row (V6 section 26)."""

    __tablename__ = "prescriptions"
    __table_args__ = (
        UniqueConstraint("visit_id", name="uq_prescriptions_visit_id"),
        Index("ix_prescriptions_citizen_id", "citizen_id"),
        Index(
            "ix_prescriptions_author_doctor_role_registration_id",
            "author_doctor_role_registration_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_visits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("citizen_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    author_doctor_role_registration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    diagnostic_information: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_advice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    items: Mapped[List["PrescriptionItem"]] = relationship(
        "PrescriptionItem",
        back_populates="prescription",
        cascade="all, delete-orphan",
        order_by="PrescriptionItem.id",
        passive_deletes=True,
    )
    document: Mapped[Optional["PrescriptionDocument"]] = relationship(
        "PrescriptionDocument",
        back_populates="prescription",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PrescriptionItem(Base):
    """One structured medicine row (V6 section 27)."""

    __tablename__ = "prescription_items"
    __table_args__ = (
        Index("ix_prescription_items_prescription_id", "prescription_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    medicine_name: Mapped[str] = mapped_column(
        String(length=200), nullable=False
    )
    dosage: Mapped[str] = mapped_column(String(length=100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(length=100), nullable=False)
    duration: Mapped[str] = mapped_column(String(length=100), nullable=False)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    prescription: Mapped["Prescription"] = relationship(
        "Prescription", back_populates="items"
    )


class PrescriptionDocument(Base):
    """Pointer to the rendered PDF binary (V6 section 28)."""

    __tablename__ = "prescription_documents"
    __table_args__ = (
        UniqueConstraint(
            "prescription_id",
            name="uq_prescription_documents_prescription_id",
        ),
        Index(
            "ix_prescription_documents_prescription_id",
            "prescription_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(length=500), nullable=False
    )
    file_name: Mapped[str] = mapped_column(
        String(length=255), nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        String(length=100),
        nullable=False,
        server_default="application/pdf",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
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

    prescription: Mapped["Prescription"] = relationship(
        "Prescription", back_populates="document"
    )


__all__ = [
    "Prescription",
    "PrescriptionDocument",
    "PrescriptionItem",
]
