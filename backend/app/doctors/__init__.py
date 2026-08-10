from __future__ import annotations

from app.doctors import (
    dependencies,
    models,
    repository,
    routes,
    schemas,
    service,
)
from app.doctors.routes import doctor_router

__all__ = [
    "dependencies",
    "models",
    "repository",
    "routes",
    "schemas",
    "service",
    "doctor_router",
]
