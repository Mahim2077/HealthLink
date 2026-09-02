from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.appointments.dependencies import (
    get_current_verified_doctor_for_chamber,
)
from app.citizens.dependencies import CitizenContext, get_current_citizen
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.prescriptions.repository import PrescriptionsRepository
from app.professionals.dependencies import ProfessionalAuthContext


@dataclass(frozen=True)
class DoctorPrescriptionAccess:
    doctor: ProfessionalAuthContext
    prescription_id: uuid.UUID


@dataclass(frozen=True)
class CitizenPrescriptionAccess:
    citizen: CitizenContext
    prescription_id: uuid.UUID


def get_doctor_prescription_access(
    prescription_id: Annotated[uuid.UUID, Path(...)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> DoctorPrescriptionAccess:
    repository = PrescriptionsRepository(db)
    prescription = repository.get_prescription_by_id(prescription_id)
    if prescription is None:
        raise HealthLinkError(
            "Prescription not found.",
            status_code=404,
        )
    if (
        prescription.author_doctor_role_registration_id
        != context.role_registration.id
    ):
        raise HealthLinkError(
            "You can only access prescriptions you authored.",
            status_code=403,
        )
    return DoctorPrescriptionAccess(
        doctor=context,
        prescription_id=prescription_id,
    )


def get_citizen_prescription_access(
    prescription_id: Annotated[uuid.UUID, Path(...)],
    context: Annotated[CitizenContext, Depends(get_current_citizen)],
    db: Annotated[Session, Depends(get_db)],
) -> CitizenPrescriptionAccess:
    repository = PrescriptionsRepository(db)
    prescription = repository.get_prescription_by_id(prescription_id)
    if prescription is None:
        raise HealthLinkError(
            "Prescription not found.",
            status_code=404,
        )
    if prescription.citizen_id != context.profile.id:
        raise HealthLinkError(
            "You can only access your own prescriptions.",
            status_code=403,
        )
    return CitizenPrescriptionAccess(
        citizen=context,
        prescription_id=prescription_id,
    )


__all__ = [
    "DoctorPrescriptionAccess",
    "CitizenPrescriptionAccess",
    "get_doctor_prescription_access",
    "get_citizen_prescription_access",
]
