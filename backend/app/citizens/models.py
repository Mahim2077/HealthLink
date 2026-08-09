from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.models import User
from app.db.base import Base


class UserNationalIdentifier(Base):
    __tablename__ = "user_national_identifiers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    nid_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
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

    user: Mapped[User] = relationship()


class CitizenProfile(Base):
    __tablename__ = "citizen_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(32), nullable=False)
    blood_group: Mapped[str | None] = mapped_column(String(8))
    address: Mapped[str | None] = mapped_column(Text)
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

    user: Mapped[User] = relationship()


class CitizenIdentifier(Base):
    __tablename__ = "citizen_identifiers"
    __table_args__ = (
        CheckConstraint(
            "national_identifier_id IS NOT NULL OR birth_certificate_number IS NOT NULL",
            name="identity_present",
        ),
        CheckConstraint(
            "registered_with IN ('NID', 'BCN')",
            name="valid_registered_with",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    national_identifier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_national_identifiers.id", ondelete="RESTRICT"),
        unique=True,
    )
    birth_certificate_number: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
    )
    registered_with: Mapped[str] = mapped_column(String(32), nullable=False)
    nid_added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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

    user: Mapped[User] = relationship()
    national_identifier: Mapped[UserNationalIdentifier | None] = relationship()
