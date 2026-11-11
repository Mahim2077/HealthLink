import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.admins.service import AdminService
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, get_current_auth_context, get_request_settings
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.professionals.dependencies import get_current_professional_context
from app.core.config import Settings, get_settings
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.reminders.inbox import InboxService
from app.reminders.schemas import ActiveInput, InboxPage, InboxUpdate, NotificationView, PrescriptionChoice, ReminderInput, ReminderView, SchedulesPage
from app.reminders.service import ReminderService

router = APIRouter(tags=["reminders"])
Citizen = Annotated[CitizenContext, Depends(get_current_citizen)]
Database = Annotated[Session, Depends(get_db)]
Page = Annotated[int, Query(ge=1, le=10000)]


@router.get("/citizens/me/reminder-schedules", response_model=SchedulesPage)
def list_schedules(citizen: Citizen, db: Database, page: Page = 1):
    return ReminderService(db).schedules_page(citizen.profile.id, page)


def current_inbox(
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    db: Database,
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> InboxService:
    if auth.portal == Portal.CITIZEN:
        recipient_id = get_current_citizen(auth, db).profile.id
    else:
        if auth.portal == Portal.ADMIN:
            AdminService(db, settings).require_active_admin(auth.user.id)
        else:
            get_current_professional_context(auth, db)
        recipient_id = auth.user.id
    return InboxService(db, auth.portal, recipient_id)


Inbox = Annotated[InboxService, Depends(current_inbox)]


@router.get("/me/inbox", response_model=InboxPage)
def list_inbox(inbox: Inbox, before: uuid.UUID | None = None):
    return inbox.page(before)


@router.post("/me/inbox/sync")
def sync_inbox(inbox: Inbox, db: Database):
    if inbox.portal == Portal.CITIZEN:
        ReminderService(db).run_due_reminders(datetime.now(UTC), citizen_id=inbox.recipient_id)
    return {"unread_count": inbox.unread_count()}


@router.post("/me/inbox/{notification_id}/read", response_model=InboxUpdate)
def mark_inbox_read(notification_id: uuid.UUID, inbox: Inbox):
    return InboxUpdate(item=inbox.mark(notification_id), unread_count=inbox.unread_count())


@router.post("/me/inbox/{notification_id}/acknowledge", response_model=InboxUpdate)
def acknowledge_inbox_item(notification_id: uuid.UUID, inbox: Inbox):
    return InboxUpdate(item=inbox.mark(notification_id, acknowledge=True), unread_count=inbox.unread_count())


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
