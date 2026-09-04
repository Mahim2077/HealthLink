from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.appointments.dependencies import (
    get_current_verified_doctor_for_chamber,
)
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.prescriptions.dependencies import (
    PrescriptionAccess,
    get_prescription_access,
)
from app.prescriptions.schemas import (
    PrescriptionCreateRequest,
    PrescriptionUpdateRequest,
    PrescriptionView,
)
from app.prescriptions.service import PrescriptionsService
from app.professionals.dependencies import ProfessionalAuthContext
from app.visits.models import MedicalVisit


visits_prescription_router = APIRouter(
    prefix="/visits",
    tags=["prescriptions"],
)

prescriptions_router = APIRouter(
    prefix="/prescriptions",
    tags=["prescriptions"],
)


@visits_prescription_router.post(
    "/{visit_id}/prescription",
    response_model=PrescriptionView,
    status_code=status.HTTP_201_CREATED,
    summary="Author a chamber prescription for a visit",
)
def create_prescription_for_visit(
    payload: PrescriptionCreateRequest,
    visit_id: Annotated[uuid.UUID, Path(...)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionView:
    visit = db.get(MedicalVisit, visit_id)
    if visit is None:
        raise HealthLinkError("Medical visit not found.", status_code=404)
    if visit.doctor_role_registration_id != context.role_registration.id:
        raise HealthLinkError(
            "Only the verified doctor who owns this visit may author the "
            "prescription.",
            status_code=403,
        )
    return PrescriptionsService(db).create_for_visit(
        doctor_role_registration_id=context.role_registration.id,
        visit_id=visit_id,
        payload=payload,
    )


@prescriptions_router.get(
    "/{prescription_id}",
    response_model=PrescriptionView,
    summary="Read a prescription as its citizen or author doctor",
)
def get_prescription(
    access: Annotated[
        PrescriptionAccess,
        Depends(get_prescription_access),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionView:
    service = PrescriptionsService(db)
    if access.actor_kind == "citizen":
        assert access.citizen_profile_id is not None
        return service.read_for_citizen(
            access.citizen_profile_id,
            access.prescription_id,
        )
    assert access.doctor_role_registration_id is not None
    return service.read_for_doctor(
        access.doctor_role_registration_id,
        access.prescription_id,
    )


@prescriptions_router.put(
    "/{prescription_id}",
    response_model=PrescriptionView,
    summary="Edit and regenerate a prescription as its author doctor",
)
def update_prescription(
    payload: PrescriptionUpdateRequest,
    access: Annotated[
        PrescriptionAccess,
        Depends(get_prescription_access),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> PrescriptionView:
    if (
        access.actor_kind != "author_doctor"
        or access.doctor_role_registration_id is None
    ):
        raise HealthLinkError(
            "Citizens cannot edit prescriptions.", status_code=403
        )
    return PrescriptionsService(db).update(
        doctor_role_registration_id=access.doctor_role_registration_id,
        prescription_id=access.prescription_id,
        payload=payload,
    )


@prescriptions_router.get(
    "/{prescription_id}/pdf",
    summary="Stream a private prescription PDF after authorization",
    response_class=Response,
)
def stream_prescription_pdf(
    access: Annotated[
        PrescriptionAccess,
        Depends(get_prescription_access),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    payload, file_name = PrescriptionsService(db).stream_pdf(
        access.prescription_id
    )
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


__all__ = ["prescriptions_router", "visits_prescription_router"]
