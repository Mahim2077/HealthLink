from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.ai.providers import AIProvider, create_ai_provider
from app.auth.dependencies import get_request_settings
from app.core.config import Settings
from app.core.exceptions import HealthLinkError


def get_ai_provider(
    request: Request,
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> AIProvider:
    provider = getattr(request.app.state, "ai_provider", None)
    if provider is None:
        try:
            provider = create_ai_provider(settings)
        except Exception as error:
            raise HealthLinkError(
                "The configured AI provider is unavailable.",
                status_code=503,
            ) from error
        request.app.state.ai_provider = provider
    return provider
