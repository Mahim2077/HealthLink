from fastapi import APIRouter

from app.admins.routes import admin_router
from app.admins.routes import auth_router as admin_auth_router
from app.appointments.routes import appointments_router
from app.appointments.routes import chamber_router
from app.auth.routes import router as auth_router
from app.citizens.routes import auth_router as citizen_auth_router
from app.citizens.routes import citizen_router
from app.doctors.routes import doctor_router
from app.prescriptions.routes import (
    prescriptions_router,
    visits_prescription_router,
)
from app.professionals.routes import auth_router as professional_auth_router
from app.professionals.routes import professional_router
from app.visits.routes import (
    citizen_visits_router,
    doctor_visits_router,
)


api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(citizen_auth_router)
api_router.include_router(citizen_router)
api_router.include_router(appointments_router)
api_router.include_router(chamber_router)
api_router.include_router(professional_auth_router)
api_router.include_router(professional_router)
api_router.include_router(admin_auth_router)
api_router.include_router(admin_router)
api_router.include_router(doctor_router)
api_router.include_router(doctor_visits_router)
api_router.include_router(citizen_visits_router)
api_router.include_router(visits_prescription_router)
api_router.include_router(prescriptions_router)
