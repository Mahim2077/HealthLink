import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmergencyProfile(Base):
    __tablename__ = "emergency_profiles"

    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), primary_key=True)
    allergies: Mapped[str | None] = mapped_column(Text)
    chronic_conditions: Mapped[str | None] = mapped_column(Text)
    current_medications: Mapped[str | None] = mapped_column(Text)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(150))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(32))
    special_notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
