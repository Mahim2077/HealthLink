from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.facilities.models import HealthcareFacility


class FacilityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, facility: HealthcareFacility) -> HealthcareFacility:
        self.db.add(facility)
        return facility

    def list(self) -> list[HealthcareFacility]:
        return list(
            self.db.scalars(
                select(HealthcareFacility).order_by(
                    HealthcareFacility.name, HealthcareFacility.created_at
                )
            )
        )

    def get_by_id(
        self, facility_id: uuid.UUID, *, for_update: bool = False
    ) -> HealthcareFacility | None:
        statement = select(HealthcareFacility).where(
            HealthcareFacility.id == facility_id
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.db.scalar(statement)
