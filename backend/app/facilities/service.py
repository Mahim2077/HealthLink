from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.admins.models import AdminActionLog
from app.facilities.models import HealthcareFacility
from app.facilities.repository import FacilityRepository
from app.facilities.schemas import FacilityWriteRequest
from app.facilities.geocoding import geocode_facility_address
from app.core.exceptions import HealthLinkError
from app.core.config import Settings
from app.auth.service import utc_now
from app.locations.service import resolve_area


class FacilityNotFoundError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Healthcare facility not found.", status_code=404)


class FacilityService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings
        self.repository = FacilityRepository(db)

    def list_facilities(self) -> list[HealthcareFacility]:
        return self.repository.list()

    def create(
        self, payload: FacilityWriteRequest, *, admin_user_id: uuid.UUID
    ) -> HealthcareFacility:
        if payload.district_code and payload.upazila_code:
            resolve_area(payload.district_code, payload.upazila_code)
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
        if payload.district_code and payload.upazila_code:
            resolve_area(payload.district_code, payload.upazila_code)
        location_changed = any(
            (
                facility.address != payload.address,
                facility.district_code != payload.district_code,
                facility.upazila_code != payload.upazila_code,
            )
        )
        for field, value in payload.model_dump().items():
            setattr(facility, field, value)
        if location_changed:
            facility.latitude = None
            facility.longitude = None
            facility.location_status = "PENDING"
            facility.location_matched_address = None
            facility.location_confirmed_at = None
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

    def confirm_location(
        self, facility_id: uuid.UUID, *, admin_user_id: uuid.UUID
    ) -> HealthcareFacility:
        if self.settings is None:
            raise RuntimeError("Settings are required to confirm a facility location.")
        facility = self.repository.get_by_id(facility_id, for_update=True)
        if facility is None:
            raise FacilityNotFoundError()
        if (
            facility.location_status == "CONFIRMED"
            and facility.latitude is not None
            and facility.longitude is not None
        ):
            return facility
        if not facility.district_code or not facility.upazila_code:
            from app.locations.service import BangladeshAreaNotFoundError

            raise BangladeshAreaNotFoundError()
        district, upazila = resolve_area(facility.district_code, facility.upazila_code)
        matched = geocode_facility_address(
            address=facility.address,
            district=district.name,
            upazila=upazila.name,
            settings=self.settings,
        )
        facility.latitude = matched.latitude
        facility.longitude = matched.longitude
        facility.location_status = "CONFIRMED"
        facility.location_matched_address = matched.matched_address
        facility.location_confirmed_at = utc_now()
        self.db.add(
            AdminActionLog(
                admin_user_id=admin_user_id,
                action_type="FACILITY_LOCATION_CONFIRM",
                target_resource_type="HEALTHCARE_FACILITY",
                target_resource_id=facility.id,
            )
        )
        self.db.commit()
        self.db.refresh(facility)
        return facility
