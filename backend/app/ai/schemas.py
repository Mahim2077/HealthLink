from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AI_SOURCE_CATEGORY = Literal[
    "PROFILE",
    "EMERGENCY_PROFILE",
    "VISITS",
    "PRESCRIPTIONS",
    "DIAGNOSTIC_REPORTS",
]


class _StrictAIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIGuidanceRequest(_StrictAIModel):
    question: str = Field(min_length=3, max_length=1_500)
    use_my_health_records: Literal[True]

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError("Question must contain at least 3 characters.")
        return normalized


class GuidanceObservation(_StrictAIModel):
    statement: str = Field(min_length=1, max_length=800)
    source_categories: list[AI_SOURCE_CATEGORY] = Field(
        min_length=1,
        max_length=5,
    )


class AIProviderGuidance(_StrictAIModel):
    summary: str = Field(min_length=1, max_length=1_200)
    record_observations: list[GuidanceObservation] = Field(
        default_factory=list,
        max_length=10,
    )
    general_guidance: list[str] = Field(default_factory=list, max_length=8)
    questions_for_clinician: list[str] = Field(default_factory=list, max_length=6)
    urgent_warning: str | None = Field(default=None, max_length=600)

    @field_validator("general_guidance", "questions_for_clinician")
    @classmethod
    def validate_list_items(cls, value: list[str]) -> list[str]:
        normalized = [" ".join(item.split()) for item in value]
        if any(not item or len(item) > 500 for item in normalized):
            raise ValueError("Guidance list items must be 1 to 500 characters.")
        return normalized


class AIContextCounts(_StrictAIModel):
    visits: int = 0
    prescriptions: int = 0
    diagnostic_reports: int = 0
    emergency_profile: int = 0


class AIGuidanceResponse(AIProviderGuidance):
    disclaimer: str
    records_used: AIContextCounts


class AIStatusResponse(_StrictAIModel):
    enabled: bool
    record_context_enabled: bool
    mode: Literal["non-diagnostic-guidance"] = "non-diagnostic-guidance"


class AIProfileContext(_StrictAIModel):
    age_group: str
    gender: str
    blood_group: str | None = None


class AIEmergencyContext(_StrictAIModel):
    allergies: str | None = None
    chronic_conditions: str | None = None
    current_medications: str | None = None
    special_notes: str | None = None


class AIVisitContext(_StrictAIModel):
    visit_date: datetime
    chief_complaint: str | None = None
    recorded_diagnosis: str | None = None
    clinical_notes: str | None = None
    follow_up_instructions: str | None = None


class AIPrescriptionItemContext(_StrictAIModel):
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None = None


class AIPrescriptionContext(_StrictAIModel):
    created_at: datetime
    diagnostic_information: str | None = None
    medical_advice: str | None = None
    notes: str | None = None
    medicines: list[AIPrescriptionItemContext] = Field(default_factory=list)


class AILabResultContext(_StrictAIModel):
    parameter: str
    result: str
    unit: str | None = None
    reference_range: str | None = None
    flag: str | None = None


class AIDiagnosticReportContext(_StrictAIModel):
    report_date: date
    test_name: str
    summary: str | None = None
    results: list[AILabResultContext] = Field(default_factory=list)


class AIRecordContext(_StrictAIModel):
    profile: AIProfileContext
    emergency_profile: AIEmergencyContext | None = None
    visits: list[AIVisitContext] = Field(default_factory=list)
    prescriptions: list[AIPrescriptionContext] = Field(default_factory=list)
    diagnostic_reports: list[AIDiagnosticReportContext] = Field(
        default_factory=list
    )

    def counts(self) -> AIContextCounts:
        return AIContextCounts(
            visits=len(self.visits),
            prescriptions=len(self.prescriptions),
            diagnostic_reports=len(self.diagnostic_reports),
            emergency_profile=int(self.emergency_profile is not None),
        )
