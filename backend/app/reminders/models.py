import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MedicineReminder(Base):
    __tablename__ = "medicine_reminders"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="valid_dates"),
        CheckConstraint("timezone = 'Asia/Dhaka'", name="supported_timezone"),
        Index("ix_medicine_reminders_citizen", "citizen_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="RESTRICT"))
    medicine: Mapped[str] = mapped_column(String(200))
    prescription_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prescription_items.id", ondelete="SET NULL"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Dhaka", server_default="Asia/Dhaka")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    schedule_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MedicineReminderTime(Base):
    __tablename__ = "medicine_reminder_times"
    __table_args__ = (UniqueConstraint("reminder_id", "daily_time", name="uq_medicine_reminder_times_reminder_time"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reminder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("medicine_reminders.id", ondelete="CASCADE"))
    daily_time: Mapped[time] = mapped_column(Time)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("kind IN ('MEDICINE','APPOINTMENT')", name="valid_kind"),
        Index("ix_notifications_citizen_due", "citizen_id", "due_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="RESTRICT"))
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    kind: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(1000))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
