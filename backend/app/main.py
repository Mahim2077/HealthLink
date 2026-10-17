from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    application_settings = settings or get_settings()
    application = FastAPI(
        title=application_settings.app_name,
        debug=application_settings.debug,
        version="0.1.0",
    )
    application.state.settings = application_settings
    application.state.ai_provider = None

    @application.middleware("http")
    async def private_authenticated_responses(request, call_next):
        response = await call_next(request)
        # Login/refresh responses also contain credentials without a bearer header.
        if request.headers.get("authorization") or request.url.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=application_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
