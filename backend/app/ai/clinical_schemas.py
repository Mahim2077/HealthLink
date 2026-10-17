from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PrescriptionMedicineEducation(_StrictModel):
    item_number: int = Field(ge=1, le=50)
    general_education: str = Field(min_length=1, max_length=700)


class PrescriptionProviderExplanation(_StrictModel):
    """Provider-authored prose only; record facts are added by the server."""

    plain_language_summary: str = Field(min_length=1, max_length=1_200)
    medicine_education: list[PrescriptionMedicineEducation] = Field(
        default_factory=list, max_length=50,
    )
    questions_to_ask_clinician: list[str] = Field(
        default_factory=list,
        max_length=6,
    )

    @field_validator("plain_language_summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("questions_to_ask_clinician")
    @classmethod
    def normalize_questions(cls, value: list[str]) -> list[str]:
        normalized = [" ".join(item.split()) for item in value]
        if any(not item or len(item) > 500 for item in normalized):
            raise ValueError("Questions must be 1 to 500 characters.")
        return normalized


class MedicineExplanation(_StrictModel):
    medicine_name: str = Field(min_length=1, max_length=200)
    purpose_or_role: str = Field(min_length=1, max_length=500)
    recorded_instructions: str = Field(min_length=1, max_length=1_200)
    general_education: str | None = Field(default=None, max_length=700)


class PrescriptionExplanationResponse(_StrictModel):
    plain_language_summary: str
    medicine_explanations: list[MedicineExplanation]
    questions_to_ask_clinician: list[str]
    disclaimer: str


class LabParameterProviderExplanation(_StrictModel):
    item_number: int = Field(ge=1, le=200)
    explanation: str = Field(min_length=1, max_length=700)

    @field_validator("explanation")
    @classmethod
    def normalize_explanation(cls, value: str) -> str:
        return " ".join(value.split())


class LabReportProviderExplanation(_StrictModel):
    summary: str = Field(min_length=1, max_length=1_200)
    parameter_explanations: list[LabParameterProviderExplanation] = Field(
        default_factory=list,
        max_length=200,
    )
    questions_for_clinician: list[str] = Field(
        default_factory=list,
        max_length=6,
    )

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("questions_for_clinician")
    @classmethod
    def normalize_questions(cls, value: list[str]) -> list[str]:
        normalized = [" ".join(item.split()) for item in value]
        if any(not item or len(item) > 500 for item in normalized):
            raise ValueError("Questions must be 1 to 500 characters.")
        return normalized


class LabParameterExplanation(_StrictModel):
    parameter: str = Field(min_length=1, max_length=150)
    result: str = Field(min_length=1, max_length=500)
    unit: str | None = Field(default=None, max_length=50)
    reference_range: str | None = Field(default=None, max_length=150)
    flag: str | None = Field(default=None, max_length=50)
    explanation: str = Field(min_length=1, max_length=700)


class FlaggedLabResult(_StrictModel):
    parameter: str = Field(min_length=1, max_length=150)
    result: str = Field(min_length=1, max_length=500)
    unit: str | None = Field(default=None, max_length=50)
    reference_range: str | None = Field(default=None, max_length=150)
    flag: str = Field(min_length=1, max_length=50)


class LabReportExplanationResponse(_StrictModel):
    summary: str
    parameter_explanations: list[LabParameterExplanation]
    flagged_results: list[FlaggedLabResult]
    questions_for_clinician: list[str]
    disclaimer: str


__all__ = [
    "FlaggedLabResult",
    "LabParameterExplanation",
    "LabParameterProviderExplanation",
    "LabReportExplanationResponse",
    "LabReportProviderExplanation",
    "MedicineExplanation",
    "PrescriptionExplanationResponse",
    "PrescriptionProviderExplanation",
]
