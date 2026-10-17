"""Shared provider boundary: deadlines, schema revalidation, and safe errors."""
from __future__ import annotations

import asyncio

from pydantic import BaseModel

from app.ai.providers import AIProvider, AIProviderRateLimitError, StructuredResponse
from app.ai.safety import UnsafeAIGuidanceError, validate_health_ai_output
from app.core.config import Settings
from app.core.exceptions import HealthLinkError


async def generate_health_output(
    provider: AIProvider,
    settings: Settings,
    prompt: str,
    response_model: type[StructuredResponse],
) -> StructuredResponse:
    try:
        raw = await asyncio.wait_for(
            provider.generate_structured(prompt, response_model),
            timeout=settings.ai_timeout_seconds,
        )
        # Do not trust a provider's annotation or even a preconstructed model.
        # Revalidate limits, extra fields and types at the application boundary.
        payload = raw.model_dump() if isinstance(raw, BaseModel) else raw
        output = response_model.model_validate(payload, strict=True)
    except TimeoutError as error:
        raise HealthLinkError(
            "The AI guidance service timed out. Please try again.",
            status_code=504,
        ) from error
    except AIProviderRateLimitError as error:
        raise HealthLinkError(
            "The AI guidance service is temporarily busy. Please try again later.",
            status_code=429,
            headers={"Retry-After": "30"},
        ) from error
    except Exception as error:
        # Provider errors and malformed output must never disclose SDK details,
        # prompts, clinical records, or credentials to a caller.
        raise HealthLinkError(
            "The AI guidance service is temporarily unavailable.",
            status_code=502,
        ) from error

    try:
        validate_health_ai_output(output)
    except UnsafeAIGuidanceError as error:
        raise HealthLinkError(
            "The AI response did not meet HealthLink safety requirements.",
            status_code=502,
        ) from error
    return output
