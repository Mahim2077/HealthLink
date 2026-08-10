from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.appointments.dependencies import (
    get_current_verified_doctor_for_chamber,
)
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.professionals.dependencies import ProfessionalAuthContext
from app.visits.repository import (
    CurrentPatientContext,
    VisitsRepository,
)


@dataclass(frozen=True)
class CurrentPatientAccess:
    """Resolved patient access context for Phase 12 doctor endpoints.

    Carries the joined queue + appointment + citizen + facility rows
    plus a flag indicating whether access was derived from the
    chamber queue (``queue``) or a manual patient grant
    (``grant``). Either path satisfies V6 section 22's "current
    patient access" rule.
    """

    context: CurrentPatientContext
    source: str  # "queue" | "grant"


def _build_access(
    *,
    registration_id: uuid.UUID,
    doctor_user_id: uuid.UUID,
    repository: VisitsRepository,
    queue_id: uuid.UUID | None = None,
) -> CurrentPatientAccess:
    del registration_id  # kept for future grant-lookup wiring
    if queue_id is not None:
        ctx = repository.load_queue_entry_for_doctor(doctor_user_id, queue_id)
        if ctx is None:
            raise HealthLinkError(
                "Queue entry is not your current chamber patient.",
                status_code=404,
            )
        return CurrentPatientAccess(context=ctx, source="queue")

    ctx = repository.load_current_patient_for_doctor(doctor_user_id)
    if ctx is not None:
        return CurrentPatientAccess(context=ctx, source="queue")

    # Manual grants are reserved for Phase 14+; Phase 12 requires an
    # active CURRENT chamber patient.
    raise HealthLinkError(
        "No current chamber patient for the verified doctor.",
        status_code=404,
    )


def get_current_patient_access_for_doctor(
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentPatientAccess | None:
    """Doctor may or may not have a current chamber patient.

    Returning ``None`` lets the workspace page render an
    "open a patient from your chamber queue first" empty state
    instead of a 404. Routes that genuinely require a current
    patient (e.g. the explicit ``start-for-current`` action)
    use the queue-id variant which still raises 404 when the
    doctor is acting on a non-current queue row.
    """

    repository = VisitsRepository(db)
    ctx = repository.load_current_patient_for_doctor(context.auth.user.id)
    if ctx is None:
        return None
    return CurrentPatientAccess(context=ctx, source="queue")


def get_current_patient_access_for_queue_entry(
    queue_id: Annotated[uuid.UUID, Path(...)],
    context: Annotated[
        ProfessionalAuthContext,
        Depends(get_current_verified_doctor_for_chamber),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentPatientAccess:
    """Doctor has a current chamber patient identified by queue row."""

    repository = VisitsRepository(db)
    return _build_access(
        registration_id=context.role_registration.id,
        doctor_user_id=context.auth.user.id,
        repository=repository,
        queue_id=queue_id,
    )


__all__ = [
    "CurrentPatientAccess",
    "get_current_patient_access_for_doctor",
    "get_current_patient_access_for_queue_entry",
]
