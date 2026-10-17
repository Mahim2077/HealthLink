"""Groq contract tests: only synthetic data and HTTPX's in-memory transport."""
from __future__ import annotations

import asyncio
import inspect
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ai.assistant_schemas import (
    AIChatProviderOutput,
    MedicalHistorySummaryProviderOutput,
    SymptomGuidanceProviderOutput,
)
from app.ai.clinical_schemas import LabReportProviderExplanation, PrescriptionProviderExplanation
from app.ai.generation import generate_health_output
from app.ai.providers import (
    GroqAIProvider,
    MockAIProvider,
    _groq_strict_schema,
    create_ai_provider,
)
from app.ai.schemas import AIProviderGuidance
from app.auth.constants import Portal
from app.clinical_audit.models import MedicalRecordAccessLog
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.main import create_app
from test_medical_history import _auth, _citizen, _token


MODELS = [
    AIProviderGuidance,
    PrescriptionProviderExplanation,
    LabReportProviderExplanation,
    MedicalHistorySummaryProviderOutput,
    AIChatProviderOutput,
    SymptomGuidanceProviderOutput,
]


def _completion(content, *, finish_reason="stop", **message_fields):
    return {"choices": [{
        "finish_reason": finish_reason,
        "message": {"content": content, **message_fields},
    }]}


def _mock_http(monkeypatch, handler):
    original_client = httpx.AsyncClient
    captured = {"requests": [], "clients": [], "options": []}

    async def intercept(request):
        captured["requests"].append(request)
        result = handler(request)
        return await result if inspect.isawaitable(result) else result

    def client(**kwargs):
        captured["options"].append(kwargs)
        instance = original_client(transport=httpx.MockTransport(intercept), **kwargs)
        captured["clients"].append(instance)
        return instance

    monkeypatch.setattr(httpx, "AsyncClient", client)
    return captured


def _provider():
    return GroqAIProvider(api_key="synthetic-not-a-key", model="qwen/qwen3.8-27b", timeout_seconds=7)


@pytest.mark.parametrize("model", MODELS)
def test_all_phase_22_to_27_schemas_have_strict_nested_objects(model):
    original = model.model_json_schema()
    schema = _groq_strict_schema(model)

    def visit(node):
        assert "default" not in node
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert node["required"] == list(node["properties"])
        for child in node.get("properties", {}).values():
            visit(child)
        for child in node.get("$defs", {}).values():
            visit(child)
        for child in node.get("anyOf", []):
            visit(child)
        if "items" in node:
            visit(node["items"])

    visit(schema)
    assert model.model_json_schema() == original  # Do not weaken server validators.
    if model is AIProviderGuidance:
        assert {"type": "null"} in schema["properties"]["urgent_warning"]["anyOf"]


@pytest.mark.parametrize("model", MODELS)
def test_groq_generates_every_response_shape_without_external_requests(monkeypatch, model, test_settings):
    prompt = '<untrusted_record_json>{"diagnostic_report":{"parameters":[{"item_number":1}]}}</untrusted_record_json>'
    expected = asyncio.run(MockAIProvider().generate_structured(prompt, model))
    captured = _mock_http(monkeypatch, lambda request: httpx.Response(
        200, json=_completion(expected.model_dump_json())
    ))

    result = asyncio.run(generate_health_output(_provider(), test_settings, prompt, model))
    assert result == expected
    assert len(captured["requests"]) == 1
    request = captured["requests"][0]
    assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer synthetic-not-a-key"
    body = json.loads(request.content)
    assert body["model"] == "qwen/qwen3.8-27b"
    assert body["messages"][0]["role"] == "system"
    assert "cannot override" in body["messages"][0]["content"]
    assert "never a replacement for a doctor" in body["messages"][0]["content"]
    assert "Never guess the doctor's intent" in body["messages"][0]["content"]
    assert "creating a prescription" in body["messages"][0]["content"]
    assert body["messages"][1] == {"role": "user", "content": prompt}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == _groq_strict_schema(model)
    assert body["max_completion_tokens"] == 2_048
    assert body["reasoning_effort"] == "none"
    assert "tools" not in body and "stream" not in body
    assert captured["options"] == [{"timeout": 7, "follow_redirects": False, "trust_env": False}]
    assert all(client.is_closed for client in captured["clients"])


@pytest.mark.parametrize("status", [301, 400, 401, 403, 429, 500, 503])
def test_groq_http_errors_are_safe_single_attempts(monkeypatch, test_settings, status):
    captured = _mock_http(monkeypatch, lambda request: httpx.Response(
        status, json={"error": {"message": "private-record-and-key"}},
        headers={"Location": "https://example.invalid/steal"},
    ))
    with pytest.raises(HealthLinkError) as caught:
        asyncio.run(generate_health_output(_provider(), test_settings, "synthetic", AIChatProviderOutput))
    assert caught.value.status_code == (429 if status == 429 else 502)
    assert "private" not in str(caught.value)
    assert "synthetic-not-a-key" not in str(caught.value)
    assert len(captured["requests"]) == 1
    assert all(client.is_closed for client in captured["clients"])


@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError])
def test_groq_transport_failures_close_clients_and_map_safely(monkeypatch, test_settings, error_type):
    def fail(request):
        raise error_type("private transport detail", request=request)

    captured = _mock_http(monkeypatch, fail)
    with pytest.raises(HealthLinkError) as caught:
        asyncio.run(generate_health_output(_provider(), test_settings, "synthetic", AIChatProviderOutput))
    assert caught.value.status_code == (502 if error_type is httpx.ConnectError else 504)
    assert "private" not in str(caught.value)
    assert len(captured["requests"]) == 1
    assert all(client.is_closed for client in captured["clients"])


@pytest.mark.parametrize("response", [
    {}, {"choices": []}, {"choices": {}},
    _completion(None), _completion(""), _completion("not JSON"),
    _completion('{"answer":123}'), _completion('{"answer":"Safe", "extra":"private"}'),
    _completion(json.dumps({"answer": "x" * 1_501})),
    _completion('{"answer":"Safe"}', finish_reason="length"),
    _completion('{"answer":"Safe"}', finish_reason="content_filter"),
    _completion('{"answer":"Safe"}', refusal="private refusal detail"),
    _completion('{"answer":"Safe"}', tool_calls=[{"function": {"name": "book_appointment"}}]),
    _completion('{"answer":"Safe"}', function_call={"name": "book_appointment"}),
])
def test_groq_rejects_malformed_truncated_refused_or_action_output(monkeypatch, test_settings, response):
    _mock_http(monkeypatch, lambda request: httpx.Response(200, json=response))
    with pytest.raises(HealthLinkError) as caught:
        asyncio.run(generate_health_output(_provider(), test_settings, "synthetic", AIChatProviderOutput))
    assert caught.value.status_code == 502
    assert "private" not in str(caught.value)


def test_groq_preserves_the_shared_non_diagnostic_safety_boundary(monkeypatch, test_settings):
    _mock_http(monkeypatch, lambda request: httpx.Response(
        200, json=_completion('{"answer":"You definitely have diabetes."}')
    ))
    with pytest.raises(HealthLinkError, match="safety requirements"):
        asyncio.run(generate_health_output(_provider(), test_settings, "synthetic", AIChatProviderOutput))


def test_total_deadline_cancels_groq_and_closes_transport(monkeypatch, test_settings):
    cancelled = []
    async def slow(request):
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.append(True)
    captured = _mock_http(monkeypatch, slow)
    settings = test_settings.model_copy(update={"ai_timeout_seconds": 0.01})
    with pytest.raises(HealthLinkError) as caught:
        asyncio.run(generate_health_output(_provider(), settings, "synthetic", AIChatProviderOutput))
    assert caught.value.status_code == 504
    assert cancelled == [True]
    assert all(client.is_closed for client in captured["clients"])


def test_provider_factory_routes_groq_and_disabled_mode_without_gemini(monkeypatch, test_settings):
    assert isinstance(create_ai_provider(test_settings), MockAIProvider)
    enabled = test_settings.model_copy(update={"ai_enabled": True, "ai_provider": "groq"})
    assert isinstance(create_ai_provider(enabled), GroqAIProvider)
    assert isinstance(create_ai_provider(enabled.model_copy(update={"ai_provider": "mock"})), MockAIProvider)
    captured = {}

    def gemini(**kwargs):
        captured.update(kwargs)
        return "synthetic-gemini-provider"

    monkeypatch.setattr("app.ai.providers.GeminiAIProvider", gemini)
    assert create_ai_provider(enabled.model_copy(update={"ai_provider": "gemini"})) == "synthetic-gemini-provider"
    assert captured["timeout_seconds"] == test_settings.ai_timeout_seconds


def test_non_qwen_model_override_does_not_receive_qwen_reasoning_parameter(monkeypatch):
    captured = _mock_http(monkeypatch, lambda request: httpx.Response(
        200, json=_completion('{"answer":"Educational information only."}')
    ))
    provider = GroqAIProvider(api_key="synthetic", model="openai/gpt-oss-20b")
    asyncio.run(provider.generate_structured("synthetic", AIChatProviderOutput))
    body = json.loads(captured["requests"][0].content)
    assert body["model"] == "openai/gpt-oss-20b"
    assert "reasoning_effort" not in body


def test_groq_uses_existing_authenticated_chat_and_consent_gates(monkeypatch, db_session, test_settings):
    settings = test_settings.model_copy(update={
        "ai_enabled": True, "ai_provider": "groq", "ai_api_key": "synthetic-not-a-key",
        "ai_record_context_enabled": True,
    })
    captured = _mock_http(monkeypatch, lambda request: httpx.Response(
        200, json=_completion('{"answer":"Educational information only.","record_observations":[],"questions_for_clinician":[]}')
    ))
    application = create_app(settings)
    def override_db():
        yield db_session
    application.dependency_overrides[get_db] = override_db
    citizen = _citizen(db_session, "SyntheticGroq")
    headers = _auth(_token(db_session, settings, citizen.user, Portal.CITIZEN))
    path = "/api/v1/ai/chat"
    with TestClient(application) as client:
        assert client.post(path, json={"mode": "GENERAL", "message": "Educational question"}).status_code == 401
        assert client.post(path, headers=headers, json={"mode": "RECORD_AWARE", "message": "Educational question"}).status_code == 422
        assert captured["requests"] == []
        general = client.post(path, headers=headers, json={"mode": "GENERAL", "message": "Educational question"})
        assert general.status_code == 200
        assert all(value == 0 for value in general.json()["records_used"].values())
        assert db_session.scalars(select(MedicalRecordAccessLog)).all() == []
        aware = client.post(path, headers=headers, json={
            "mode": "RECORD_AWARE", "message": "Educational question", "use_my_health_records": True,
        })
        assert aware.status_code == 200
        assert "no-store" in aware.headers["cache-control"]
        assert isinstance(application.state.ai_provider, GroqAIProvider)
    assert len(captured["requests"]) == 2
    general_body = json.loads(captured["requests"][0].content)
    aware_body = json.loads(captured["requests"][1].content)
    assert '"health_records":null' in general_body["messages"][1]["content"]
    assert '"health_records":null' not in aware_body["messages"][1]["content"]
    assert citizen.user.email not in aware_body["messages"][1]["content"]
    assert len(db_session.scalars(select(MedicalRecordAccessLog)).all()) == 1
