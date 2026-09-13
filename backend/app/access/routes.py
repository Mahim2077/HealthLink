from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.access.policy import ClinicalReadPolicy
from app.auth.dependencies import AuthContext, get_current_auth_context
from app.auth.models import User
from app.auth.service import as_utc
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.citizens.models import CitizenProfile
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.professionals.models import HealthcareProfessionalProfile, ProfessionalRole, ProfessionalRoleRegistration
from app.visits.models import PatientAccessGrant, PatientAccessScope

router = APIRouter(tags=["access-grants"])
Database = Annotated[Session, Depends(get_db)]
Citizen = Annotated[CitizenContext, Depends(get_current_citizen)]


class GrantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    professional_role_registration_id: UUID
    access_scope: PatientAccessScope
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def future_expiry(cls, value):
        if value is not None and (value.tzinfo is None or as_utc(value) <= datetime.now(UTC)):
            raise ValueError("Expiry must be a future date with a time zone.")
        return value


def _view(grant, db):
    registration = db.get(ProfessionalRoleRegistration, grant.professional_role_registration_id)
    user = registration.professional.user
    return {"id": grant.id, "professional_role_registration_id": registration.id,
            "professional_name": f"{user.first_name} {user.last_name}".strip(),
            "role": registration.role.code, "designation": registration.designation,
            "access_scope": grant.access_scope, "granted_at": grant.granted_at,
            "expires_at": grant.expires_at, "revoked_at": grant.revoked_at,
            "active": grant.revoked_at is None and (grant.expires_at is None or as_utc(grant.expires_at) > datetime.now(UTC))}


@router.get("/citizens/me/access-grant-professionals")
def professionals(citizen: Citizen, db: Database, search: Annotated[str, Query(max_length=100)] = ""):
    statement = select(ProfessionalRoleRegistration, User).join(HealthcareProfessionalProfile,
        HealthcareProfessionalProfile.id == ProfessionalRoleRegistration.professional_id).join(User,
        User.id == HealthcareProfessionalProfile.user_id).join(ProfessionalRole,
        ProfessionalRole.id == ProfessionalRoleRegistration.role_id).where(
        ProfessionalRoleRegistration.verification_status == "VERIFIED", ProfessionalRole.is_active.is_(True),
        ProfessionalRole.code == "DOCTOR", User.is_active.is_(True))
    if search.strip():
        pattern = "%" + search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        statement = statement.where(or_(User.first_name.ilike(pattern, escape="\\"), User.last_name.ilike(pattern, escape="\\"), ProfessionalRoleRegistration.designation.ilike(pattern, escape="\\")))
    return [{"id": role.id, "name": f"{user.first_name} {user.last_name}".strip(),
             "role": role.role.code, "designation": role.designation,
             "facility_name": role.facility.name if role.facility else role.facility_name_submitted}
            for role, user in db.execute(statement.order_by(User.first_name, User.last_name, ProfessionalRoleRegistration.id).limit(50))]


@router.get("/citizens/me/access-grants")
def list_grants(citizen: Citizen, db: Database, page: Annotated[int, Query(ge=1, le=10000)] = 1):
    rows = db.scalars(select(PatientAccessGrant).where(PatientAccessGrant.citizen_id == citizen.profile.id)
        .order_by(PatientAccessGrant.granted_at.desc(), PatientAccessGrant.id).offset((page - 1) * 20).limit(21)).all()
    return {"grants": [_view(row, db) for row in rows[:20]], "page": page, "has_next": len(rows) > 20}


@router.post("/citizens/me/access-grants", status_code=201)
def create_grant(payload: GrantInput, citizen: Citizen, db: Database):
    registration = db.get(ProfessionalRoleRegistration, payload.professional_role_registration_id)
    if (registration is None or registration.verification_status != "VERIFIED"
        or not registration.role.is_active or registration.role.code != "DOCTOR"
        or not registration.professional.user.is_active):
        raise HealthLinkError("Select a verified Doctor.", status_code=422)
    # Serialize consent changes per citizen; duplicate requests cannot create duplicate active grants.
    db.scalar(select(CitizenProfile).where(CitizenProfile.id == citizen.profile.id).with_for_update())
    existing = db.scalar(select(PatientAccessGrant).where(PatientAccessGrant.citizen_id == citizen.profile.id,
        PatientAccessGrant.professional_role_registration_id == registration.id,
        PatientAccessGrant.access_scope == payload.access_scope.value, PatientAccessGrant.revoked_at.is_(None),
        or_(PatientAccessGrant.expires_at.is_(None), PatientAccessGrant.expires_at > datetime.now(UTC))))
    if existing:
        raise HealthLinkError("An active grant for this doctor and scope already exists.", status_code=409)
    grant = PatientAccessGrant(citizen_id=citizen.profile.id,
        professional_role_registration_id=registration.id, access_scope=payload.access_scope.value,
        granted_at=datetime.now(UTC), expires_at=payload.expires_at)
    db.add(grant)
    db.flush()
    from app.clinical_audit.service import AuditService
    AuditService(db).record(auth=citizen.auth, citizen_id=citizen.profile.id,
        resource_type="ACCESS_GRANT", resource_id=grant.id, action="GRANT", commit=False)
    db.commit()
    return _view(grant, db)


@router.post("/citizens/me/access-grants/{grant_id}/revoke")
def revoke_grant(grant_id: UUID, citizen: Citizen, db: Database):
    grant = db.scalar(select(PatientAccessGrant).where(PatientAccessGrant.id == grant_id,
        PatientAccessGrant.citizen_id == citizen.profile.id).with_for_update())
    if grant is None:
        raise HealthLinkError("Access grant not found.", status_code=404)
    if grant.revoked_at is None:
        grant.revoked_at = datetime.now(UTC)
        from app.clinical_audit.service import AuditService
        AuditService(db).record(auth=citizen.auth, citizen_id=citizen.profile.id,
            resource_type="ACCESS_GRANT", resource_id=grant.id, action="REVOKE", commit=False)
        db.commit()
    return _view(grant, db)


@router.get("/professionals/me/access-grants")
def granted_patients(auth: Annotated[AuthContext, Depends(get_current_auth_context)], db: Database,
                     page: Annotated[int, Query(ge=1, le=10000)] = 1):
    registration = ClinicalReadPolicy(db).doctor(auth)
    rows = db.execute(select(PatientAccessGrant, CitizenProfile, User).join(CitizenProfile,
        CitizenProfile.id == PatientAccessGrant.citizen_id).join(User, User.id == CitizenProfile.user_id).where(
        PatientAccessGrant.professional_role_registration_id == registration.id,
        PatientAccessGrant.revoked_at.is_(None), or_(PatientAccessGrant.expires_at.is_(None),
        PatientAccessGrant.expires_at > datetime.now(UTC))).order_by(PatientAccessGrant.granted_at.desc(),
        PatientAccessGrant.id).offset((page - 1) * 20).limit(21)).all()
    return {"grants": [{"id": grant.id, "citizen_id": citizen.id,
        "citizen_name": f"{user.first_name} {user.last_name}".strip(), "access_scope": grant.access_scope,
        "expires_at": grant.expires_at} for grant, citizen, user in rows[:20]], "page": page, "has_next": len(rows) > 20}
