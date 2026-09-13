import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MedicalRecordAccessLog(Base):
    __tablename__ = "medical_record_access_logs"
    __table_args__ = (Index("ix_medical_access_citizen_created", "citizen_id", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    actor_professional_role_registration_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"))
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="RESTRICT"))
    facility_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("healthcare_facilities.id", ondelete="RESTRICT"))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[str | None] = mapped_column(String(100))
    access_source: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
