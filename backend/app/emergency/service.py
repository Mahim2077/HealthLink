import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.citizens.models import CitizenProfile
from app.core.exceptions import HealthLinkError
from app.emergency.models import EmergencyProfile
from app.emergency.schemas import EmergencyProfileInput, EmergencyProfileView


class EmergencyProfileService:
    def __init__(self, db: Session):
        self.db = db

    def read(self, citizen_id: uuid.UUID) -> EmergencyProfileView:
        citizen = self.db.get(CitizenProfile, citizen_id)
        if citizen is None:
            raise HealthLinkError("Citizen profile not found.", status_code=404)
        row = self.db.get(EmergencyProfile, citizen_id)
        fields = {name: getattr(row, name) for name in EmergencyProfileInput.model_fields} if row else {}
        return EmergencyProfileView(citizen_id=citizen_id, blood_group=citizen.blood_group, updated_at=row.updated_at if row else None, **fields)

    def save(self, citizen_id: uuid.UUID, payload: EmergencyProfileInput) -> EmergencyProfileView:
        # Serialize first creation as well as updates: the citizen exists before
        # the optional emergency profile, so it is a stable upsert lock target.
        citizen = self.db.scalar(select(CitizenProfile).where(CitizenProfile.id == citizen_id).with_for_update())
        if citizen is None:
            raise HealthLinkError("Citizen profile not found.", status_code=404)
        row = self.db.scalar(select(EmergencyProfile).where(EmergencyProfile.citizen_id == citizen_id).execution_options(populate_existing=True))
        if row is None:
            row = EmergencyProfile(citizen_id=citizen_id)
            self.db.add(row)
        for name, value in payload.model_dump().items():
            setattr(row, name, value)
        self.db.commit()
        self.db.refresh(row)
        return self.read(citizen_id)
