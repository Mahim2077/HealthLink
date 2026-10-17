from __future__ import annotations

import asyncio
import json
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel

from app.ai.schemas import AIProviderGuidance
from app.ai.policy import HEALTHLINK_SYSTEM_PROMPT
from app.core.config import Settings


StructuredResponse = TypeVar("StructuredResponse", bound=BaseModel)

_SYSTEM_BOUNDARY = HEALTHLINK_SYSTEM_PROMPT


class AIProviderError(Exception):
    """A provider failure safe to translate without leaking provider details."""


class AIProviderRateLimitError(AIProviderError):
    pass


class AIProvider(Protocol):
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[StructuredResponse],
    ) -> StructuredResponse: ...


class MockAIProvider:
    """Deterministic no-network provider for local development and CI."""

    async def generate_structured(
        self,
        _prompt: str,
        response_model: type[StructuredResponse],
    ) -> StructuredResponse:
        if response_model is AIProviderGuidance:
            guidance = AIProviderGuidance(
                summary=(
                    "Your available HealthLink records were reviewed for general "
                    "informational guidance."
                ),
                general_guidance=[
                    "Discuss any new, worsening, or persistent symptoms with a qualified clinician."
                ],
                questions_for_clinician=[
                    "Are any follow-up checks appropriate based on my recorded history?"
                ],
            )
            return response_model.model_validate(guidance.model_dump())

        # Imports remain local so the shared provider module does not create
        # schema/service import cycles.
        from app.ai.assistant_schemas import (
            AIChatProviderOutput,
            MedicalHistorySummaryProviderOutput,
            SymptomGuidanceProviderOutput,
            UrgencyCategory,
        )
        from app.ai.clinical_schemas import (
            LabParameterProviderExplanation,
            LabReportProviderExplanation,
            PrescriptionProviderExplanation,
        )

        if response_model is PrescriptionProviderExplanation:
            return response_model(
                plain_language_summary=(
                    "The recorded prescription is shown below in plain language."
                ),
                questions_to_ask_clinician=[
                    "What is each recorded medicine intended to address?"
                ],
            )
        if response_model is LabReportProviderExplanation:
            item_numbers = self._lab_item_numbers(_prompt)
            return response_model(
                summary=(
                    "This finalized diagnostic report contains recorded laboratory results."
                ),
                parameter_explanations=[
                    LabParameterProviderExplanation(
                        item_number=item_number,
                        explanation=(
                            "This is the value recorded by the laboratory; a clinician "
                            "can interpret it in the context of your health."
                        ),
                    )
                    for item_number in item_numbers
                ],
                questions_for_clinician=[
                    "How should these recorded results be interpreted in my context?"
                ],
            )
        if response_model is MedicalHistorySummaryProviderOutput:
            return response_model(
                summary=(
                    "The HealthLink record contains a bounded set of finalized health records."
                ),
                questions_for_clinician=[
                    "What follow-up is appropriate based on my recorded history?"
                ],
            )
        if response_model is AIChatProviderOutput:
            return response_model(
                answer=(
                    "This is general educational information to help prepare a discussion "
                    "with a qualified clinician."
                ),
                questions_for_clinician=[
                    "What details would help a clinician assess this concern?"
                ],
            )
        if response_model is SymptomGuidanceProviderOutput:
            return response_model(
                symptom_summary="The described symptoms need cautious monitoring.",
                general_information=[
                    "Many different health issues can cause similar symptoms."
                ],
                red_flags=[
                    "Severe or rapidly worsening symptoms warrant urgent evaluation."
                ],
                suggested_next_step=(
                    "Seek clinical review if symptoms persist or worsen."
                ),
                urgency_category=UrgencyCategory.ROUTINE_CLINICAL_REVIEW,
            )
        raise AIProviderError(
            "No deterministic mock is registered for this AI response."
        )

    @staticmethod
    def _lab_item_numbers(prompt: str) -> list[int]:
        marker = "<untrusted_record_json>"
        end_marker = "</untrusted_record_json>"
        if marker not in prompt or end_marker not in prompt:
            return []
        raw = prompt.split(marker, 1)[1].split(end_marker, 1)[0]
        try:
            payload = json.loads(raw)
            parameters = payload["diagnostic_report"]["parameters"]
            return [int(item["item_number"]) for item in parameters]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return []


class GeminiAIProvider:
    """Native Gemini adapter isolated behind the HealthLink provider protocol."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float = 20) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:  # pragma: no cover - deployment packaging guard
            raise AIProviderError("The configured AI provider is unavailable.") from error
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=max(1, int(timeout_seconds * 1_000)),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        self._types = types
        self._model = model

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[StructuredResponse],
    ) -> StructuredResponse:
        try:
            return await asyncio.to_thread(
                self._generate_sync,
                prompt,
                response_model,
            )
        except AIProviderError:
            raise
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            if status_code == 429 or "429" in str(error):
                raise AIProviderRateLimitError(
                    "The AI guidance service is temporarily busy."
                ) from error
            raise AIProviderError(
                "The AI guidance service could not complete the request."
            ) from error

    def _generate_sync(
        self,
        prompt: str,
        response_model: type[StructuredResponse],
    ) -> StructuredResponse:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=_SYSTEM_BOUNDARY,
                temperature=0.1,
                max_output_tokens=2_048,
                response_mime_type="application/json",
                response_schema=response_model,
            ),
        )
        output_text = getattr(response, "text", None)
        if not output_text:
            raise AIProviderError("The AI guidance service returned no result.")
        try:
            return response_model.model_validate_json(output_text)
        except ValueError as error:
            raise AIProviderError(
                "The AI guidance service returned an invalid result."
            ) from error


def _groq_strict_schema(response_model: type[BaseModel]) -> dict:
    """Project Pydantic schemas to the provider's structural JSON subset.

    Every property is required, including nullable/defaulted properties. Nested
    objects forbid additional fields. Length/range/custom validators remain on
    the original Pydantic model and are always applied after generation; we do
    not depend on the provider implementing those JSON Schema keywords.
    """
    def convert(node: dict) -> dict:
        result = {
            key: value
            for key, value in node.items()
            if key in {"type", "$ref", "enum", "description"}
        }
        if "const" in node:
            result["enum"] = [node["const"]]
        for key in ("$defs", "properties"):
            if key in node:
                result[key] = {
                    name: convert(child) for name, child in node[key].items()
                }
        if "items" in node:
            result["items"] = convert(node["items"])
        if "anyOf" in node:
            result["anyOf"] = [convert(child) for child in node["anyOf"]]
        if node.get("type") == "object":
            result["required"] = list(result.get("properties", {}))
            result["additionalProperties"] = False
        return result

    return convert(response_model.model_json_schema())


class GroqAIProvider:
    """Direct GroqCloud adapter; no OpenAI account or SDK is involved.

    The fixed HTTPS destination cannot be redirected by environment or user
    input. Per-request async clients close on completion/cancellation. HTTPX
    performs no implicit retries, and the shared generation boundary enforces
    the total deadline and application safety/grounding checks.
    """

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float = 20) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[StructuredResponse],
    ) -> StructuredResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_BOUNDARY},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_completion_tokens": 2_048,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": _groq_strict_schema(response_model),
                },
            },
        }
        if self._model.startswith("qwen/qwen3"):
            # Educational prose does not need a hidden thinking-token budget.
            payload["reasoning_effort"] = "none"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
            if response.status_code == 429:
                raise AIProviderRateLimitError("The AI service is temporarily busy.")
            if response.status_code != 200:
                raise AIProviderError("The AI service could not complete the request.")
            choices = response.json()["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise AIProviderError("The AI service returned an invalid result.")
            choice = choices[0]
            message = choice["message"]
            # Reject truncated output, refusals and tool actions, even when a
            # fragment happens to parse as JSON. Never execute model tools.
            if (
                choice["finish_reason"] != "stop"
                or message.get("refusal")
                or message.get("tool_calls")
                or message.get("function_call")
            ):
                raise AIProviderError("The AI service returned no usable result.")
            output_text = message["content"]
            if not isinstance(output_text, str) or not output_text.strip():
                raise AIProviderError("The AI service returned no result.")
            return response_model.model_validate_json(output_text, strict=True)
        except httpx.TimeoutException as error:
            raise TimeoutError("The AI service timed out.") from error
        except AIProviderError:
            raise
        except Exception as error:
            # Do not include provider bodies, URLs, prompts or credentials in
            # errors. The API boundary presents a fixed generic message.
            raise AIProviderError("The AI service returned an invalid result.") from error


def create_ai_provider(settings: Settings) -> AIProvider:
    if not settings.ai_enabled or settings.ai_provider == "mock":
        return MockAIProvider()
    provider_type = GroqAIProvider if settings.ai_provider == "groq" else GeminiAIProvider
    return provider_type(
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
    )
