"""Derived longitudinal medical-record views."""

from app.medical_records.routes import (
    citizen_medical_history_router,
    professional_medical_history_router,
)

__all__ = [
    "citizen_medical_history_router",
    "professional_medical_history_router",
]
