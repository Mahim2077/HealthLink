from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.medical_records.repository import MedicalHistoryRepository
from app.medical_records.schemas import (
    MedicalHistoryEvent,
    MedicalHistoryPage,
    MedicalHistoryQuery,
    MedicalHistoryResourceType,
)


class MedicalHistoryService:
    def __init__(self, db: Session) -> None:
        self.repository = MedicalHistoryRepository(db)

    def list_history(
        self,
        citizen_id: uuid.UUID,
        query: MedicalHistoryQuery,
    ) -> MedicalHistoryPage:
        rows, total = self.repository.list_events(
            citizen_id,
            resource_type=query.resource_type,
            date_from=query.date_from,
            date_to=query.date_to,
            offset=(query.page - 1) * query.page_size,
            limit=query.page_size,
        )
        items = []
        for row in rows:
            resource_type = MedicalHistoryResourceType(row["resource_type"])
            full_name = " ".join(
                part
                for part in (
                    row["professional_first_name"],
                    row["professional_last_name"],
                )
                if part
            ).strip()
            subtitle = row["subtitle"]
            if (
                resource_type is MedicalHistoryResourceType.PRESCRIPTION
                and row["item_count"] is not None
            ):
                count = int(row["item_count"])
                subtitle = f"{count} medicine" + ("" if count == 1 else "s")
            resource_id = row["resource_id"]
            items.append(
                MedicalHistoryEvent(
                    id=f"{resource_type.value.lower()}:{resource_id}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    occurred_at=row["occurred_at"],
                    title=row["title"],
                    subtitle=subtitle,
                    facility=row["facility_name"],
                    professional=(f"Dr {full_name}" if full_name else None),
                    status=row["status"],
                    summary=row["summary"],
                    appointment_id=row["appointment_id"],
                    serial_number=row["serial_number"],
                )
            )
        return MedicalHistoryPage(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total=total,
            has_next=query.page * query.page_size < total,
        )


__all__ = ["MedicalHistoryService"]
