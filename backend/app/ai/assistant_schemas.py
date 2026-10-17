from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ai.schemas import AIContextCounts, GuidanceObservation


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MedicalHistorySummaryRequest(_StrictModel):
    use_my_health_records: Literal[True]


class MedicalHistorySummaryProviderOutput(_StrictModel):
    summary: str = Field(min_length=1, max_length=1_500)
    record_observations: list[GuidanceObservation] = Field(
        default_factory=list,
        max_length=12,
    )
    questions_for_clinician: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return _normalize_text(value)

    @field_validator("questions_for_clinician")
    @classmethod
    def normalize_questions(cls, value: list[str]) -> list[str]:
        normalized = [_normalize_text(item) for item in value]
        if any(not item or len(item) > 500 for item in normalized):
            raise ValueError("Questions must contain 1 to 500 characters.")
        return normalized


class MedicalHistorySummaryResponse(MedicalHistorySummaryProviderOutput):
    disclaimer: str
    records_used: AIContextCounts


class ChatMode(StrEnum):
    GENERAL = "GENERAL"
    RECORD_AWARE = "RECORD_AWARE"


class AIChatRequest(_StrictModel):
    mode: ChatMode
    message: str = Field(min_length=3, max_length=1_500)
    use_my_health_records: bool = False

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = _normalize_text(value)
        if len(normalized) < 3:
            raise ValueError("Message must contain at least 3 characters.")
        return normalized

    @model_validator(mode="after")
    def require_explicit_record_consent(self) -> "AIChatRequest":
        if self.mode is ChatMode.RECORD_AWARE and not self.use_my_health_records:
            raise ValueError(
                "RECORD_AWARE mode requires use_my_health_records=true."
            )
        if self.mode is ChatMode.GENERAL and self.use_my_health_records:
            raise ValueError(
                "GENERAL mode cannot use HealthLink medical records."
            )
        return self


class AIChatProviderOutput(_StrictModel):
    answer: str = Field(min_length=1, max_length=1_500)
    record_observations: list[GuidanceObservation] = Field(
        default_factory=list,
        max_length=10,
    )
    questions_for_clinician: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        return _normalize_text(value)

    @field_validator("questions_for_clinician")
    @classmethod
    def normalize_questions(cls, value: list[str]) -> list[str]:
        normalized = [_normalize_text(item) for item in value]
        if any(not item or len(item) > 500 for item in normalized):
            raise ValueError("Questions must contain 1 to 500 characters.")
        return normalized


class AIChatResponse(AIChatProviderOutput):
    disclaimer: str
    records_used: AIContextCounts


class UrgencyCategory(StrEnum):
    SELF_CARE_INFORMATION = "SELF_CARE_INFORMATION"
    ROUTINE_CLINICAL_REVIEW = "ROUTINE_CLINICAL_REVIEW"
    PROMPT_CLINICAL_REVIEW = "PROMPT_CLINICAL_REVIEW"
    URGENT_OR_EMERGENCY_EVALUATION = "URGENT_OR_EMERGENCY_EVALUATION"


class SymptomGuidanceRequest(_StrictModel):
    symptoms: str = Field(min_length=3, max_length=1_500)

    @field_validator("symptoms")
    @classmethod
    def normalize_symptoms(cls, value: str) -> str:
        normalized = _normalize_text(value)
        if len(normalized) < 3:
            raise ValueError("Symptoms must contain at least 3 characters.")
        return normalized


class SymptomGuidanceProviderOutput(_StrictModel):
    symptom_summary: str = Field(min_length=1, max_length=800)
    general_information: list[str] = Field(default_factory=list, max_length=8)
    red_flags: list[str] = Field(default_factory=list, max_length=8)
    suggested_next_step: str = Field(min_length=1, max_length=600)
    urgency_category: UrgencyCategory

    @field_validator("symptom_summary", "suggested_next_step")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        return _normalize_text(value)

    @field_validator("general_information", "red_flags")
    @classmethod
    def normalize_list_fields(cls, value: list[str]) -> list[str]:
        normalized = [_normalize_text(item) for item in value]
        if any(not item or len(item) > 500 for item in normalized):
            raise ValueError("Guidance items must contain 1 to 500 characters.")
        return normalized


class SymptomGuidanceResponse(SymptomGuidanceProviderOutput):
    disclaimer: str


__all__ = [
    "AIChatProviderOutput",
    "AIChatRequest",
    "AIChatResponse",
    "ChatMode",
    "MedicalHistorySummaryProviderOutput",
    "MedicalHistorySummaryRequest",
    "MedicalHistorySummaryResponse",
    "SymptomGuidanceProviderOutput",
    "SymptomGuidanceRequest",
    "SymptomGuidanceResponse",
    "UrgencyCategory",
]
