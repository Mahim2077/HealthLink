from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HealthcareFacility(Base):
    __tablename__ = "healthcare_facilities"
    __table_args__ = (
        CheckConstraint(
            "facility_type IN ('HOSPITAL', 'CLINIC', 'DIAGNOSTIC_CENTER', 'PHARMACY')",
            name="valid_facility_type",
        ),
        Index("ix_healthcare_facilities_name", "name"),
        Index(
            "ix_healthcare_facilities_area",
            "district_code",
            "upazila_code",
            "location_status",
        ),
        CheckConstraint(
            "location_status IN ('PENDING', 'CONFIRMED')",
            name="valid_location_status",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude BETWEEN 20 AND 27)",
            name="valid_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude BETWEEN 88 AND 93)",
            name="valid_longitude",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(50), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text, nullable=False)
    district_code: Mapped[str | None] = mapped_column(String(16))
    upazila_code: Mapped[str | None] = mapped_column(String(20))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    location_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="PENDING", server_default="PENDING"
    )
    location_matched_address: Mapped[str | None] = mapped_column(Text)
    location_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(320))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
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
