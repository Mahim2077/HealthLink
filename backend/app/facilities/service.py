from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.admins.models import AdminActionLog
from app.facilities.models import HealthcareFacility
from app.facilities.repository import FacilityRepository
from app.facilities.schemas import FacilityWriteRequest
from app.core.exceptions import HealthLinkError


class FacilityNotFoundError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Healthcare facility not found.", status_code=404)


class FacilityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = FacilityRepository(db)

    def list_facilities(self) -> list[HealthcareFacility]:
        return self.repository.list()

    def create(
        self, payload: FacilityWriteRequest, *, admin_user_id: uuid.UUID
    ) -> HealthcareFacility:
        facility = self.repository.add(HealthcareFacility(**payload.model_dump()))
        self.db.flush()
        self.db.add(
            AdminActionLog(
                admin_user_id=admin_user_id,
                action_type="FACILITY_CREATE",
                target_resource_type="HEALTHCARE_FACILITY",
                target_resource_id=facility.id,
            )
        )
        self.db.commit()
        self.db.refresh(facility)
        return facility

    def update(
        self,
        facility_id: uuid.UUID,
        payload: FacilityWriteRequest,
        *,
        admin_user_id: uuid.UUID,
    ) -> HealthcareFacility:
        facility = self.repository.get_by_id(facility_id, for_update=True)
        if facility is None:
            raise FacilityNotFoundError()
        for field, value in payload.model_dump().items():
            setattr(facility, field, value)
        self.db.add(
            AdminActionLog(
                admin_user_id=admin_user_id,
                action_type="FACILITY_UPDATE",
                target_resource_type="HEALTHCARE_FACILITY",
                target_resource_id=facility.id,
            )
        )
        self.db.commit()
        self.db.refresh(facility)
        return facility
