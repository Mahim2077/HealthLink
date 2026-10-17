from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel

from app.ai.schemas import AIProviderGuidance


class UnsafeAIGuidanceError(ValueError):
    pass


_DIAGNOSIS_PATTERNS = (
    # Disease-agnostic patient conclusions: a named-condition list is not a
    # safety boundary. Recorded facts should use source-labelled wording.
    re.compile(r"\byou\s+(?:(?:probably|likely|possibly|may|might|could|do|definitely|certainly|clearly)\s+)*(?:have|suffer\s+from|are\s+suffering\s+from)\b(?!(?:\s+(?:asked|described|mentioned|questions?|records?|reports?|appointments?|prescriptions?)\b))", re.I),
    re.compile(r"\b(?:your\s+(?:symptoms|results|tests)|you)\b.{0,50}\b(?:suggest|indicate|point\s+to|consistent\s+with|likely\s+to\s+be|suffering\s+from)\b", re.I),
    re.compile(r"আপনার\s+[^।\n]{0,70}(?:হয়েছে|হয়েছে|আছে|হয়েইছে|হতে\s+পারে)|আপনি\s+[^।\n]{0,70}(?:রোগে|আক্রান্ত|ভুগছেন)"),
    re.compile(r"\b(?:i|we)\s+diagnos(?:e|ed)\b", re.I),
    re.compile(r"\byou\s+(?:definitely|certainly|clearly)\s+have\b", re.I),
    re.compile(
        r"\byou\s+have\s+(?:an?\s+)?(?:infection|disease|disorder|syndrome|"
        r"cancer|diabetes|hypertension|asthma|pneumonia|flu|covid)\b",
        re.I,
    ),
    re.compile(r"\byou\s+are\s+suffering\s+from\b", re.I),
    re.compile(r"\b(?:the|your)\s+diagnosis\s+is\b", re.I),
    re.compile(r"\bthis\s+(?:confirms|proves)\b", re.I),
)
_TREATMENT_PATTERNS = (
    re.compile(r"\b(?:dose|dosage|regimen|prescription)\s*[:=-]\s*\d", re.I),
    re.compile(r"\b(?:\d+(?:\.\d+)?|one|two|three|half)\s*(?:mg|mcg|ml|tablets?|capsules?)\b.{0,35}\b(?:daily|twice|every|per\s+day|at\s+night|bid|tid|qid|qd|q\d+h)\b", re.I),
    re.compile(r"(?:^|[\n;])\s*(?:rx\s*[:=]|℞\s*[:=]?)\s*\S", re.I),
    re.compile(r"[০-৯\d]+\s*(?:মিলিগ্রাম|ট্যাবলেট|ক্যাপসুল|mg|ml)[^।\n]{0,35}(?:দিনে|প্রতিদিন|বার)"),
    # Catch directives for an unfamiliar medicine without knowing its name.
    # Narrow non-treatment exceptions retain ordinary clinician-referral UX.
    re.compile(r"(?:^|[.!?;:\n,]\s*)(?:please\s+)?(?:take|start|stop|discontinue|increase|decrease|double|halve|switch\s+to|use|try)\s+(?!(?:a\s+list|a\s+note|notes?|questions?|this\s+report|the\s+report|your\s+(?:report|questions)|keeping|tracking|monitoring|discussing|speaking|contacting)\b)\S+", re.I),
    re.compile(r"\byou\s+(?:should|must|can|need\s+to|ought\s+to|could)\s+(?:(?:consider|begin)\s+)?(?:take|taking|start|stop|use|try|switch|increase|decrease|double|halve|discontinue)\b", re.I),
    re.compile(r"\b(?:recommend(?:ed)?|suggest(?:ed)?)\s+(?:that\s+you\s+)?(?:take|taking|start|starting|stop|stopping|use|using|switch|increase|decrease)\b", re.I),
    re.compile(r"\b(?:your\s+doctor\s+(?:prescribed|gave|chose|selected).{0,80}\b(?:because|to\s+treat)|this\s+(?:medicine|medication)\s+was\s+prescribed\s+(?:because|for))\b", re.I),
    re.compile(r"(?:^|[।.!?;:\n,]\s*)(?:আপনি\s+)?[^।.!?;:\n]{0,50}(?:নিন|খান|খাবেন|শুরু\s+করুন|বন্ধ\s+করুন|বাড়ান|বাড়ান|কমান|বদলান)(?:\s|$|[।.!?])"),
    re.compile(r"(?:ওষুধ|ঔষধ|ডোজ|মাত্রা)[^।\n]{0,40}(?:নেওয়া|নেওয়া|খাওয়া|খাওয়া|বাড়ানো|বাড়ানো|কমানো|বন্ধ\s+করা)[^।\n]{0,10}(?:উচিত|দরকার)"),
    re.compile(
        r"\b(?:start|stop|discontinue|increase|decrease|double|halve|change)\b"
        r".{0,50}\b(?:medicine|medication|dose|dosage|tablet|capsule|treatment)\b",
        re.I,
    ),
    re.compile(
        r"\btake\s+(?:\d+(?:\.\d+)?|one|two|three|four|five|six)\s*"
        r"(?:mg|mcg|g|ml|tablet|capsule)s?\b",
        re.I,
    ),
    re.compile(r"\bi\s+(?:recommend|prescribe)\b.{0,80}\b(?:medicine|medication|drug|dose)\b", re.I),
    # A medication name may appear without the words 'medicine' or 'dose'.
    # Reject direct prescribing language and personalized recommendations even
    # for an unfamiliar drug, while allowing referral/discussion language.
    re.compile(r"\b(?:i|we)\s+(?:would\s+)?prescrib(?:e|ed|ing)\b", re.I),
    re.compile(
        r"\b(?:i|we)\s+(?:would\s+)?(?:recommend|suggest)\s+"
        r"(?!(?:consulting|consultation|discussing|discussion|speaking|seeking|"
        r"talking|asking|keeping|tracking|monitoring|seeing|a\s+discussion)\b)\S+",
        re.I,
    ),
    re.compile(
        r"\b(?:take|start|stop|increase|decrease|double|halve|switch\s+to)\s+"
        r"(?:your\s+)?(?:paracetamol|acetaminophen|ibuprofen|aspirin|amoxicillin|"
        r"azithromycin|metformin|insulin|amlodipine|losartan|atorvastatin|"
        r"omeprazole|prednisone|prednisolone|warfarin|salbutamol|cetirizine)\b",
        re.I,
    ),
)

_ACTION_PATTERNS = (
    re.compile(
        r"\b(?:i|we)\s+(?:have\s+|will\s+|am\s+)?"
        r"(?:order(?:ed|ing)?|book(?:ed|ing)?|schedul(?:e|ed|ing)|"
        r"cancel(?:led|ed|ing)?|chang(?:e|ed|ing)|writ(?:e|ing)|wrote|record(?:ed|ing)?)"
        r"\b.{0,60}\b(?:test|appointment|diagnosis|clinical\s+record|prescription)\b",
        re.I,
    ),
)

# Narrow fail-safe, not a general symptom checker. Severe breathing difficulty
# and tight/heavy/crushing chest pain are warning signs in these primary sources:
# https://www.nhs.uk/symptoms/shortness-of-breath/
# https://www.nhs.uk/conditions/heart-attack/
_EMERGENCY_WARNING_PATTERNS = (
    re.compile(r"\b(?:severe|extreme)\s+(?:difficulty\s+breathing|breathing\s+difficulty|shortness\s+of\s+breath)\b", re.I),
    re.compile(r"\b(?:can(?:not|'t|’t)|unable\s+to)\s+breathe\b", re.I),
    re.compile(r"\b(?:gasping\s+for\s+(?:air|breath)|choking)\b", re.I),
    re.compile(r"\b(?:severe|crushing|squeezing)\s+chest\s+(?:pain|pressure)\b", re.I),
    re.compile(r"\b(?:chest\s+(?:feels?\s+)?(?:tight|heavy)|(?:tightness|heaviness)\s+in\s+(?:my\s+|the\s+)?chest)\b", re.I),
)


def has_explicit_emergency_warning(symptoms: str) -> bool:
    """Conservatively recognize a small set of severe English warning phrases.

    A negative result says nothing about safety; the normal cautious guidance
    path remains responsible for other symptoms and languages.
    """
    for pattern in _EMERGENCY_WARNING_PATTERNS:
        for match in pattern.finditer(symptoms):
            prefix = symptoms[max(0, match.start() - 30):match.start()].lower()
            if re.search(r"(?:\bno|\bwithout|\bnot experiencing|\bdo not have|\bdon't have)\s*$", prefix):
                continue
            return True
    return False


def validate_non_diagnostic_guidance(guidance: AIProviderGuidance) -> None:
    """Reject model output that crosses into diagnosis or treatment changes."""

    validate_health_ai_output(guidance)


def _iter_text(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, BaseModel):
        yield from _iter_text(value.model_dump())
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_text(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_text(item)


def validate_health_ai_output(output: BaseModel) -> None:
    """Apply diagnosis and treatment boundaries to any structured AI result."""

    # Validate each field independently: a negation in one field must not
    # neutralize a directive in the next. Normalize simple formatting evasions.
    for text in _iter_text(output):
        normalized = unicodedata.normalize("NFKC", text)
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Cf")
        normalized = re.sub(r"[*`_]", "", normalized)
        normalized = re.sub(r"[^\S\n]+", " ", normalized).strip()
        if any(pattern.search(normalized) for pattern in _DIAGNOSIS_PATTERNS):
            raise UnsafeAIGuidanceError("AI output attempted a diagnosis.")
        if any(pattern.search(normalized) for pattern in _ACTION_PATTERNS):
            raise UnsafeAIGuidanceError("AI output claimed an unauthorized clinical action.")
        for pattern in _TREATMENT_PATTERNS:
            for match in pattern.finditer(normalized):
                prefix = normalized[max(0, match.start() - 12) : match.start()].lower()
                if prefix.endswith(("do not ", "don't ", "never ", "avoid ")):
                    continue
                raise UnsafeAIGuidanceError("AI output attempted a treatment change.")


def validate_source_grounding(
    guidance: AIProviderGuidance,
    *,
    available_sources: set[str],
) -> None:
    for observation in guidance.record_observations:
        if any(
            source not in available_sources
            for source in observation.source_categories
        ):
            raise UnsafeAIGuidanceError(
                "AI output cited a record category that was not supplied."
            )
