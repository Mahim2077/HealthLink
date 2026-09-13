from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.auth.dependencies import AuthContext, get_current_auth_context
from app.access.policy import ClinicalReadPolicy
from app.clinical_audit.service import AuditService
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.emergency.schemas import EmergencyProfileInput, EmergencyProfileView
from app.emergency.service import EmergencyProfileService
from app.visits.dependencies import CurrentPatientAccess, get_current_patient_access_for_doctor

router = APIRouter(tags=["emergency-profile"])
Database = Annotated[Session, Depends(get_db)]


@router.get("/citizens/me/emergency-profile", response_model=EmergencyProfileView)
def read_own(citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Database):
    return EmergencyProfileService(db).read(citizen.profile.id)


@router.put("/citizens/me/emergency-profile", response_model=EmergencyProfileView)
def save_own(payload: EmergencyProfileInput, citizen: Annotated[CitizenContext, Depends(get_current_citizen)], db: Database):
    return EmergencyProfileService(db).save(citizen.profile.id, payload)


@router.get("/professionals/current-patient/emergency-profile", response_model=EmergencyProfileView)
def read_current(
    auth: Annotated[AuthContext, Depends(get_current_auth_context)],
    access: Annotated[CurrentPatientAccess | None, Depends(get_current_patient_access_for_doctor)],
    db: Database,
    citizen_id: Annotated[uuid.UUID, Query()],
):
    # The expected citizen prevents an old consultation screen from displaying
    # the next queued patient's emergency information after a queue change.
    if access is None or access.context.citizen.id != citizen_id:
        raise HealthLinkError("No matching current chamber patient.", status_code=404)
    decision = ClinicalReadPolicy(db).authorize(auth, citizen_id, "EMERGENCY_PROFILE")
    result = EmergencyProfileService(db).read(citizen_id)
    AuditService(db).record(auth=auth, citizen_id=citizen_id, resource_type="EMERGENCY_PROFILE", access_source=decision.source)
    return result
