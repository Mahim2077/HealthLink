from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.prescriptions.dependencies import (
    CitizenPrescriptionAccess,
    DoctorPrescriptionAccess,
    get_citizen_prescription_access,
    get_doctor_prescription_access,
)
from app.prescriptions.schemas import (
    PrescriptionCreateRequest,
    PrescriptionUpdateRequest,
    PrescriptionView,
)
from app.prescriptions.service import PrescriptionsService
from app.professionals.dependencies import ProfessionalAuthContext
from app.appointments.dependencies import (
    get_current_verified_doctor_for_chamber,
)
from app.visits.models import MedicalVisit


doctor_visits_prescription_router = APIRouter(
    prefix="/doctors/me/visits",
    tags=["doctor-prescriptions"],
)


doctor_prescription_router = APIRouter(
    prefix="/doctors/me/prescriptions",
    tags=["doctor-prescriptions"],
)


citizen_prescription_router = APIRouter(
    prefix="/citizens/me/prescriptions",
    tags=["citizen-prescriptions"],
)


prescription_pdf_router = APIRouter(
    prefix="/prescriptions",
    tags=["prescriptions"],
)


def get_doctor_prescription_access_for_visit(
    visit_id: Annotated[uuid.UUID, Path(...)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> DoctorPrescriptionAccess:
    # Doctor-side guard scoped to a visit_id (create path).
    visit = db.get(MedicalVisit, visit_id)
    if visit is None:
        raise HTTPException(
            status_code=404, detail="Medical visit not found."
        )
    if visit.doctor_role_registration_id != context.role_registration.id:
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the verified doctor who owns this visit may "
                "author the prescription."
            ),
        )
    return DoctorPrescriptionAccess(
        doctor=context,
        prescription_id=uuid.uuid4(),
    )


@doctor_visits_prescription_router.post(
    "/{visit_id}/prescription",
    response_model=PrescriptionView,
    status_code=status.HTTP_201_CREATED,
    summary="Author a chamber prescription for the given visit",
)
def create_prescription_for_visit(
    payload: PrescriptionCreateRequest,
    visit_id: Annotated[uuid.UUID, Path(...)],
    access: Annotated[
        DoctorPrescriptionAccess,
        Depends(get_doctor_prescription_access_for_visit),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionView:
    service = PrescriptionsService(db)
    return service.create_for_visit(
        doctor_role_registration_id=access.doctor.role_registration.id,
        visit_id=visit_id,
        payload=payload,
    )


@doctor_prescription_router.get(
    "/{prescription_id}",
    response_model=PrescriptionView,
    summary="Read a prescription authored by the verified doctor",
)
def get_doctor_prescription(
    access: Annotated[
        DoctorPrescriptionAccess,
        Depends(get_doctor_prescription_access),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionView:
    service = PrescriptionsService(db)
    return service.read_for_doctor(
        doctor_role_registration_id=access.doctor.role_registration.id,
        prescription_id=access.prescription_id,
    )


@doctor_prescription_router.put(
    "/{prescription_id}",
    response_model=PrescriptionView,
    summary="Edit a prescription authored by the verified doctor",
)
def update_doctor_prescription(
    payload: PrescriptionUpdateRequest,
    access: Annotated[
        DoctorPrescriptionAccess,
        Depends(get_doctor_prescription_access),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionView:
    service = PrescriptionsService(db)
    return service.update(
        doctor_role_registration_id=access.doctor.role_registration.id,
        prescription_id=access.prescription_id,
        payload=payload,
    )


@citizen_prescription_router.get(
    "/{prescription_id}",
    response_model=PrescriptionView,
    summary="Citizen view of one of their prescriptions",
)
def get_citizen_prescription(
    access: Annotated[
        CitizenPrescriptionAccess,
        Depends(get_citizen_prescription_access),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionView:
    service = PrescriptionsService(db)
    return service.read_for_citizen(
        citizen_id=access.citizen.profile.id,
        prescription_id=access.prescription_id,
    )


@prescription_pdf_router.get(
    "/{prescription_id}/pdf",
    summary="Stream the rendered PDF for a prescription",
    response_class=Response,
)
def stream_prescription_pdf(
    access: Annotated[
        DoctorPrescriptionAccess,
        Depends(get_doctor_prescription_access),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    service = PrescriptionsService(db)
    payload, file_name = service.stream_pdf(access.prescription_id)
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "inline; filename=\"" + file_name + "\""
            ),
            "Cache-Control": "private, no-store",
        },
    )


__all__ = [
    "citizen_prescription_router",
    "doctor_prescription_router",
    "doctor_visits_prescription_router",
    "prescription_pdf_router",
]
