import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.core.exceptions import HealthLinkError
from app.reminders.models import Notification
from app.reminders.schemas import InboxPage


def record_notice(
    db: Session,
    *,
    kind: str,
    message: str,
    dedupe_key: str,
    citizen_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    portal: Portal = Portal.CITIZEN,
    due_at: datetime | None = None,
) -> int:
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    statement = insert(Notification).values(
        id=uuid.uuid4(), citizen_id=citizen_id, user_id=user_id, portal=portal.value,
        kind=kind, message=message, dedupe_key=dedupe_key, due_at=due_at or datetime.now(UTC),
    ).on_conflict_do_nothing(index_elements=["dedupe_key"]).returning(Notification.id)
    return int(db.execute(statement).scalar_one_or_none() is not None)


class InboxService:
    def __init__(self, db: Session, portal: Portal, recipient_id: uuid.UUID):
        self.db = db
        self.portal = portal
        self.recipient_id = recipient_id
        owner = Notification.citizen_id if portal == Portal.CITIZEN else Notification.user_id
        self.scope = and_(Notification.portal == portal.value, owner == recipient_id)

    def _owned(self, notification_id: uuid.UUID, *, lock: bool = False) -> Notification:
        query = select(Notification).where(self.scope, Notification.id == notification_id)
        row = self.db.scalar(query.with_for_update() if lock else query)
        if row is None:
            raise HealthLinkError("Notification not found.", status_code=404)
        return row

    def unread_count(self) -> int:
        return self.db.scalar(
            select(func.count()).select_from(Notification).where(self.scope, Notification.read_at.is_(None))
        )

    def page(self, before: uuid.UUID | None = None) -> InboxPage:
        query = select(Notification).where(self.scope)
        if before:
            cursor = self._owned(before)
            query = query.where(or_(
                Notification.due_at < cursor.due_at,
                and_(Notification.due_at == cursor.due_at, Notification.id < cursor.id),
            ))
        rows = list(self.db.scalars(query.order_by(Notification.due_at.desc(), Notification.id.desc()).limit(21)))
        return InboxPage(
            items=rows[:20],
            next_cursor=rows[19].id if len(rows) > 20 else None,
            unread_count=self.unread_count(),
        )

    def mark(self, notification_id: uuid.UUID, *, acknowledge: bool = False) -> Notification:
        row = self._owned(notification_id, lock=True)
        now = datetime.now(UTC)
        row.read_at = row.read_at or now
        if acknowledge:
            row.acknowledged_at = row.acknowledged_at or now
        self.db.commit()
        return row
