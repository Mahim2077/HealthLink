"""Reminder creation and retry-safe generation, without treatment recommendations."""
import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.auth.models import User
from app.core.exceptions import HealthLinkError
from app.facilities.models import HealthcareFacility
from app.prescriptions.models import Prescription, PrescriptionItem
from app.professionals.models import HealthcareProfessionalProfile, ProfessionalRoleRegistration
from app.reminders.models import MedicineReminder, MedicineReminderTime, Notification
from app.reminders.schemas import PrescriptionChoice, ReminderInput, ReminderView
from app.visits.models import MedicalVisit

DHAKA = ZoneInfo("Asia/Dhaka")


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class ReminderService:
    def __init__(self, db: Session):
        self.db = db

    def _owned(self, citizen_id, reminder_id):
        row = self.db.scalar(select(MedicineReminder).where(MedicineReminder.id == reminder_id, MedicineReminder.citizen_id == citizen_id).with_for_update())
        if row is None:
            raise HealthLinkError("Reminder not found.", status_code=404)
        return row

    def view(self, row):
        return ReminderView(id=row.id, medicine=row.medicine, prescription_item_id=row.prescription_item_id,
            start_date=row.start_date, end_date=row.end_date, timezone=row.timezone, is_active=row.is_active,
            times=list(self.db.scalars(select(MedicineReminderTime.daily_time).where(MedicineReminderTime.reminder_id == row.id).order_by(MedicineReminderTime.daily_time))))

    def list_reminders(self, citizen_id, page=1):
        return [self.view(row) for row in self.db.scalars(select(MedicineReminder).where(MedicineReminder.citizen_id == citizen_id).order_by(MedicineReminder.created_at.desc(), MedicineReminder.id).offset((page - 1) * 20).limit(20))]

    def prescription_choices(self, citizen_id, page=1):
        rows = self.db.execute(select(PrescriptionItem, MedicalVisit).join(Prescription, Prescription.id == PrescriptionItem.prescription_id).join(MedicalVisit, MedicalVisit.id == Prescription.visit_id).where(Prescription.citizen_id == citizen_id, MedicalVisit.status == "FINALIZED").order_by(MedicalVisit.created_at.desc(), PrescriptionItem.id).offset((page - 1) * 50).limit(50))
        return [PrescriptionChoice(id=item.id, medicine=item.medicine_name, dosage=item.dosage, prescription_date=visit.created_at.date()) for item, visit in rows]

    def save(self, citizen_id, payload: ReminderInput, reminder_id=None):
        row = self._owned(citizen_id, reminder_id) if reminder_id else MedicineReminder(citizen_id=citizen_id)
        if payload.prescription_item_id:
            item = self.db.scalar(select(PrescriptionItem).join(Prescription).join(MedicalVisit, MedicalVisit.id == Prescription.visit_id).where(PrescriptionItem.id == payload.prescription_item_id, Prescription.citizen_id == citizen_id, MedicalVisit.status == "FINALIZED"))
            if item is None:
                raise HealthLinkError("Choose an item from your finalized prescriptions.", status_code=422)
            if item.medicine_name != payload.medicine:
                raise HealthLinkError("Medicine must match the selected prescription item.", status_code=422)
        for key, value in payload.model_dump(exclude={"times"}).items():
            setattr(row, key, value)
        # Changes apply forward from now; editing/reactivating never fabricates missed doses.
        row.schedule_updated_at = datetime.now(UTC)
        self.db.add(row)
        self.db.flush()
        self.db.execute(delete(MedicineReminderTime).where(MedicineReminderTime.reminder_id == row.id))
        self.db.add_all(MedicineReminderTime(reminder_id=row.id, daily_time=value) for value in payload.times)
        self.db.commit()
        return self.view(row)

    def set_active(self, citizen_id, reminder_id, active):
        row = self._owned(citizen_id, reminder_id)
        if row.is_active != active:
            row.is_active = active
            row.schedule_updated_at = datetime.now(UTC)
        self.db.commit()
        return self.view(row)

    def list_notifications(self, citizen_id, page=1):
        return list(self.db.scalars(select(Notification).where(Notification.citizen_id == citizen_id).order_by(Notification.due_at.desc(), Notification.id).offset((page - 1) * 20).limit(20)))

    def mark_notification(self, citizen_id, notification_id, acknowledge=False):
        row = self.db.scalar(select(Notification).where(Notification.id == notification_id, Notification.citizen_id == citizen_id).with_for_update())
        if row is None:
            raise HealthLinkError("Notification not found.", status_code=404)
        now = datetime.now(UTC)
        row.read_at = row.read_at or now
        if acknowledge:
            row.acknowledged_at = row.acknowledged_at or now
        self.db.commit()
        return row

    def _insert_notification(self, **values):
        # ON CONFLICT runs atomically in the database, including independent workers.
        dialect = self.db.get_bind().dialect.name
        insert = pg_insert if dialect == "postgresql" else sqlite_insert
        result = self.db.execute(insert(Notification).values(id=uuid.uuid4(), **values).on_conflict_do_nothing(index_elements=["dedupe_key"]).returning(Notification.id))
        return int(result.scalar_one_or_none() is not None)

    def run_due_reminders(self, now: datetime) -> dict[str, int]:
        if now.tzinfo is None:
            raise ValueError("Reminder worker requires a timezone-aware datetime.")
        now = now.astimezone(UTC)
        since = now - timedelta(hours=24)
        created = 0
        # Stream a bounded age window; yield_per bounds Python memory for larger accounts.
        rows = self.db.execute(select(MedicineReminder, MedicineReminderTime.daily_time).join(MedicineReminderTime, MedicineReminderTime.reminder_id == MedicineReminder.id).where(MedicineReminder.is_active.is_(True), MedicineReminder.start_date <= now.astimezone(DHAKA).date()).order_by(MedicineReminder.id, MedicineReminderTime.daily_time).with_for_update(of=MedicineReminder).execution_options(yield_per=200))
        for row, daily_time in rows:
            day = since.astimezone(DHAKA).date()
            last_day = now.astimezone(DHAKA).date()
            while day <= last_day:
                due = datetime.combine(day, daily_time, DHAKA).astimezone(UTC)
                if row.start_date <= day and (row.end_date is None or day <= row.end_date) and since < due <= now and aware(row.schedule_updated_at) <= due:
                    created += self._insert_notification(citizen_id=row.citizen_id, kind="MEDICINE", message=f"Medicine reminder: {row.medicine}. Scheduled for {day.isoformat()} at {daily_time.strftime('%H:%M')} (Asia/Dhaka).", due_at=due, dedupe_key=f"medicine:{row.id}:{day.isoformat()}:{daily_time.strftime('%H:%M')}")
                day += timedelta(days=1)
        # A daily notice for booked serial appointments; no personal consultation time.
        appointments = self.db.execute(select(Appointment, HealthcareFacility.name, User.first_name, User.last_name).join(HealthcareFacility, HealthcareFacility.id == Appointment.facility_id).join(ProfessionalRoleRegistration, ProfessionalRoleRegistration.id == Appointment.doctor_role_registration_id).join(HealthcareProfessionalProfile, HealthcareProfessionalProfile.id == ProfessionalRoleRegistration.professional_id).join(User, User.id == HealthcareProfessionalProfile.user_id).where(Appointment.status == "BOOKED", Appointment.appointment_date == now.astimezone(DHAKA).date()).execution_options(yield_per=200))
        for appointment, facility, first_name, last_name in appointments:
            due = max(datetime.combine(appointment.appointment_date, time.min, DHAKA).astimezone(UTC), aware(appointment.booked_at))
            if since < due <= now:
                created += self._insert_notification(citizen_id=appointment.citizen_id, kind="APPOINTMENT", message=f"Appointment on {appointment.appointment_date.isoformat()} with Dr. {first_name} {last_name} at {facility}. Serial {appointment.serial_number}. Your serial is a queue position; check the live queue for progress.", due_at=due, dedupe_key=f"appointment:{appointment.id}:{appointment.appointment_date.isoformat()}")
        self.db.commit()
        return {"created": created}
