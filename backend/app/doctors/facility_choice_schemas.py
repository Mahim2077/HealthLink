from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class DoctorFacilityChoice(BaseModel):
    """Lightweight facility option for the doctor's own schedule editor.

    Public locality, address and facility registration distinguish same-name
    choices. Personal identifiers, contact details and coordinates stay absent.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    facility_type: str
    area: str | None = None
    address: str | None = None
    registration_number: str | None = None
    is_active: bool
    is_verified_assignment: bool


__all__ = ["DoctorFacilityChoice"]
