import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthContext
from app.auth.models import User
from app.clinical_audit.models import MedicalRecordAccessLog
from app.facilities.models import HealthcareFacility
from app.professionals.models import ProfessionalRole, ProfessionalRoleRegistration


class AccessHistoryItem(BaseModel):
    id: uuid.UUID
    actor_name: str
    role: str | None
    facility: str | None
    resource_type: str
    action: str
    access_source: str | None
    created_at: datetime


class AccessHistoryPage(BaseModel):
    items: list[AccessHistoryItem]
    page: int
    has_next: bool


class AuditService:
    """Only metadata is accepted: no clinical text or request bodies belong here."""
    def __init__(self, db: Session):
        self.db = db

    def record(self, *, auth: AuthContext | None, citizen_id: uuid.UUID,
               resource_type: str, resource_id: uuid.UUID | None = None,
               action: str = "READ", access_source: str | None = None,
               request_id: str | None = None, commit: bool = True):
        role_id = auth.session.active_professional_role_registration_id if auth and auth.portal.value == "PROFESSIONAL" else None
        role = self.db.get(ProfessionalRoleRegistration, role_id) if role_id else None
        event = MedicalRecordAccessLog(
            actor_user_id=auth.user.id if auth else None,
            actor_professional_role_registration_id=role_id,
            citizen_id=citizen_id, facility_id=role.facility_id if role else None,
            resource_type=resource_type, resource_id=resource_id, action=action,
            access_source=access_source, request_id=request_id,
        )
        self.db.add(event)
        if commit:
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
        return event

    def list_owned(self, citizen_id: uuid.UUID, page: int) -> AccessHistoryPage:
        rows = self.db.execute(
            select(MedicalRecordAccessLog, User, ProfessionalRole.name, HealthcareFacility.name)
            .outerjoin(User, User.id == MedicalRecordAccessLog.actor_user_id)
            .outerjoin(ProfessionalRoleRegistration, ProfessionalRoleRegistration.id == MedicalRecordAccessLog.actor_professional_role_registration_id)
            .outerjoin(ProfessionalRole, ProfessionalRole.id == ProfessionalRoleRegistration.role_id)
            .outerjoin(HealthcareFacility, HealthcareFacility.id == MedicalRecordAccessLog.facility_id)
            .where(MedicalRecordAccessLog.citizen_id == citizen_id)
            .order_by(MedicalRecordAccessLog.created_at.desc(), MedicalRecordAccessLog.id.desc())
            .offset((page - 1) * 20).limit(21)
        ).all()
        return AccessHistoryPage(page=page, has_next=len(rows) > 20, items=[
            AccessHistoryItem(id=event.id, actor_name=f"{user.first_name} {user.last_name}" if user else "HealthLink system",
                role=role, facility=facility, resource_type=event.resource_type, action=event.action,
                access_source=event.access_source, created_at=event.created_at)
            for event, user, role, facility in rows[:20]
        ])
