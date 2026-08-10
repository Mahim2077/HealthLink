from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class DoctorFacilityChoice(BaseModel):
    """Lightweight facility option for the doctor's own schedule editor.

    Deliberately omits address, phone, email, and registration_number —
    those are operational details. The doctor only needs enough
    information to pick the correct facility for a weekly window.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    facility_type: str
    is_active: bool
    is_verified_assignment: bool


__all__ = ["DoctorFacilityChoice"]
