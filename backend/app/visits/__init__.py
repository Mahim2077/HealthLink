"""Visits & prescriptions package.

Phase 12 builds the doctor's consultation workspace on top of the
chamber queue introduced by Phase 11. Phase 13 (diagnostics & lab
reports) and Phase 14 (prescriptions, reminders, emergency, audit)
extend the same package.
"""
from app.visits.routes import (
    citizen_visits_router,
    doctor_visits_router,
)

__all__ = ["citizen_visits_router", "doctor_visits_router"]
