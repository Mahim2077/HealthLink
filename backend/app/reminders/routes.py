import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.config import Settings, get_settings
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.reminders.schemas import ActiveInput, NotificationView, PrescriptionChoice, ReminderInput, ReminderView
from app.reminders.service import ReminderService

router = APIRouter(tags=["reminders"])
Citizen = Annotated[CitizenContext, Depends(get_current_citizen)]
Database = Annotated[Session, Depends(get_db)]
Page = Annotated[int, Query(ge=1, le=10000)]


@router.get("/citizens/me/reminders", response_model=list[ReminderView])
def list_reminders(citizen: Citizen, db: Database, page: Page = 1):
    return ReminderService(db).list_reminders(citizen.profile.id, page)


@router.get("/citizens/me/reminder-prescription-items", response_model=list[PrescriptionChoice])
def prescription_choices(citizen: Citizen, db: Database, page: Page = 1):
    return ReminderService(db).prescription_choices(citizen.profile.id, page)


@router.post("/citizens/me/reminders", response_model=ReminderView, status_code=201)
def create_reminder(payload: ReminderInput, citizen: Citizen, db: Database):
    return ReminderService(db).save(citizen.profile.id, payload)


@router.put("/citizens/me/reminders/{reminder_id}", response_model=ReminderView)
def edit_reminder(reminder_id: uuid.UUID, payload: ReminderInput, citizen: Citizen, db: Database):
    return ReminderService(db).save(citizen.profile.id, payload, reminder_id)


@router.put("/citizens/me/reminders/{reminder_id}/active", response_model=ReminderView)
def set_active(reminder_id: uuid.UUID, payload: ActiveInput, citizen: Citizen, db: Database):
    return ReminderService(db).set_active(citizen.profile.id, reminder_id, payload.is_active)


@router.get("/citizens/me/notifications", response_model=list[NotificationView])
def list_notifications(citizen: Citizen, db: Database, page: Page = 1):
    return ReminderService(db).list_notifications(citizen.profile.id, page)


@router.post("/citizens/me/notifications/{notification_id}/read", response_model=NotificationView)
def read_notification(notification_id: uuid.UUID, citizen: Citizen, db: Database):
    return ReminderService(db).mark_notification(citizen.profile.id, notification_id)


@router.post("/citizens/me/notifications/{notification_id}/acknowledge", response_model=NotificationView)
def acknowledge_notification(notification_id: uuid.UUID, citizen: Citizen, db: Database):
    return ReminderService(db).mark_notification(citizen.profile.id, notification_id, acknowledge=True)


def require_cron_secret(settings: Annotated[Settings, Depends(get_settings)], authorization: Annotated[str | None, Header()] = None):
    if not settings.cron_secret:
        raise HealthLinkError("Reminder scheduler is not configured.", status_code=503)
    if not secrets.compare_digest((authorization or "").encode(), f"Bearer {settings.cron_secret}".encode()):
        raise HealthLinkError("Unauthorized.", status_code=401)


@router.get("/jobs/reminders", dependencies=[Depends(require_cron_secret)])
def run_reminders(db: Database):
    return ReminderService(db).run_due_reminders(datetime.now(UTC))
