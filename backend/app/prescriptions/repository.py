"""Phase 13 persistence helpers for prescriptions.

Thin layer over SQLAlchemy queries; the business logic that enforces the
author-only edit invariant and regenerates the PDF lives in the service
module.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.prescriptions.models import (
    Prescription,
    PrescriptionDocument,
    PrescriptionItem,
)
from app.visits.models import MedicalVisit


class PrescriptionsRepository:
    """SQLAlchemy helpers used by the Phase 13 service + routes.

    Mirrors the pattern used by :class:`app.visits.repository.VisitsRepository`
    � methods are class-bound to a session so callers (service and
    dependencies) don't need to thread the session through themselves.
    """

    def __init__(self, db: Session) -> None:
        self.session = db
        self.db = db

    # ------------------------------------------------------------------
    # Prescription lookups
    # ------------------------------------------------------------------

    def get_prescription_for_visit(
        self, visit_id: uuid.UUID
    ) -> Prescription | None:
        stmt = (
            select(Prescription)
            .where(Prescription.visit_id == visit_id)
            .options(
                selectinload(Prescription.items),
                selectinload(Prescription.document),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_prescription_by_id(
        self, prescription_id: uuid.UUID
    ) -> Prescription | None:
        stmt = (
            select(Prescription)
            .where(Prescription.id == prescription_id)
            .options(
                selectinload(Prescription.items),
                selectinload(Prescription.document),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_visit_for_prescription(
        self, prescription: Prescription
    ) -> MedicalVisit | None:
        """Resolve the visit that owns ``prescription``.

        Centralised here so the doctor and citizen access guards in
        ``dependencies`` share the same query shape.
        """

        return self.db.get(MedicalVisit, prescription.visit_id)

    def get_document_for_prescription(
        self, prescription_id: uuid.UUID
    ) -> PrescriptionDocument | None:
        stmt = select(PrescriptionDocument).where(
            PrescriptionDocument.prescription_id == prescription_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    def replace_items(
        self, prescription: Prescription, items: list[PrescriptionItem]
    ) -> None:
        """Delete and replace items for an existing prescription.

        The service is responsible for setting the row attributes; this
        helper just swaps the child collection in a way that the cascade
        can safely clean up.
        """

        prescription.items.clear()
        self.db.flush()
        for item in items:
            prescription.items.append(item)
        self.db.flush()


__all__ = [
    "PrescriptionsRepository",
]
