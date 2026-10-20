"""Saved chat ownership, safety, retry, persistence and deletion contracts."""
import json
import uuid
from datetime import UTC, datetime
from sqlalchemy import func, select
from app.ai.conversation_models import AIConversation, AIConversationTurn
from app.auth.constants import Portal
from test_ai_assistant_phases_25_27 import AssistantProvider, _client, _enabled_settings
from test_medical_history import _auth, _citizen, _facility, _professional, _token, _visit

ROOT = "/api/v1/ai/conversations"
SEND = "/api/v1/ai/conversation-messages"


def payload(conversation_id=None, *, mode="GENERAL", message="What is a reference range?"):
    return dict(conversation_id=conversation_id, client_request_id=str(uuid.uuid4()), mode=mode, message=message, use_my_health_records=mode == "RECORD_AWARE")


def setup(db, settings):
    citizen = _citizen(db, "ChatOwner")
    other = _citizen(db, "OtherOwner")
    provider = AssistantProvider()
    settings = _enabled_settings(settings)
    return citizen, other, provider, settings, _auth(_token(db, settings, citizen.user, Portal.CITIZEN)), _auth(_token(db, settings, other.user, Portal.CITIZEN))


def test_saved_chat_reopens_continues_and_deletes(db_session, test_settings):
    owner, other, provider, settings, headers, other_headers = setup(db_session, test_settings)
    with _client(settings, db_session, provider) as client:
        first = client.post(SEND, headers=headers, json=payload())
        assert first.status_code == 200, first.text
        assert first.headers["cache-control"] == "private, no-store"
        cid = first.json()["conversation"]["id"]
        second = client.post(SEND, headers=headers, json=payload(cid, message="Explain that more simply."))
        assert second.status_code == 200, second.text
        history = json.loads(provider.prompts[-1].split("\n")[-1])["conversation_history"]
        assert history[0]["question"] == "What is a reference range?"
        detail = client.get(f"{ROOT}/{cid}", headers=headers)
        assert len(detail.json()["turns"]) == 2
        assert client.get(ROOT, headers=headers).json()["items"][0]["id"] == cid
        assert client.get(ROOT, headers=other_headers).json()["items"] == []
        assert client.get(f"{ROOT}/{cid}", headers=other_headers).status_code == 404
        assert client.post(SEND, headers=other_headers, json=payload(cid)).status_code == 404
        assert client.delete(f"{ROOT}/{cid}", headers=other_headers).status_code == 404
        assert client.delete(f"{ROOT}/{cid}", headers=headers).status_code == 204
        assert client.get(f"{ROOT}/{cid}", headers=headers).status_code == 404
        assert client.get(ROOT, headers=headers).json()["items"] == []
    assert db_session.scalar(select(func.count()).select_from(AIConversationTurn)) == 0


def test_retry_is_idempotent_and_conflicting_ids_rejected(db_session, test_settings):
    _, _, provider, settings, headers, _ = setup(db_session, test_settings)
    body = payload()
    with _client(settings, db_session, provider) as client:
        first = client.post(SEND, headers=headers, json=body).json()
        assert client.post(SEND, headers=headers, json=body).json() == first
        assert len(provider.prompts) == 1
        assert client.post(SEND, headers=headers, json={**body, "message": "A changed question"}).status_code == 409
    assert db_session.scalar(select(func.count()).select_from(AIConversation)) == 1


def test_records_consent_and_general_history_isolation(db_session, test_settings):
    owner, _, provider, settings, headers, _ = setup(db_session, test_settings)
    facility = _facility(db_session)
    _, professional = _professional(db_session, facility)
    _visit(db_session, citizen=owner, registration=professional, facility=facility, finalized_at=datetime.now(UTC), diagnosis="Private recorded concern")
    with _client(settings, db_session, provider) as client:
        body = payload(mode="RECORD_AWARE")
        assert client.post(SEND, headers=headers, json={**body, "use_my_health_records": False}).status_code == 422
        first = client.post(SEND, headers=headers, json=body)
        assert first.status_code == 200, first.text
        cid = first.json()["conversation"]["id"]
        assert first.json()["turn"]["response"]["records_used"]["visits"] == 1
        for _ in range(2):
            result = client.post(SEND, headers=headers, json=payload(cid, message="What does this mean generally?"))
            assert result.status_code == 200, result.text
            data = json.loads(provider.prompts[-1].split("\n")[-1])
            assert data["health_records"] is None
            assert data["conversation_history"] == []
        assert client.post(SEND, headers=headers, json=payload(cid, mode="RECORD_AWARE")).status_code == 200
        assert len(json.loads(provider.prompts[-1].split("\n")[-1])["conversation_history"]) == 3


def test_failed_unsafe_generation_is_not_saved(db_session, test_settings):
    _, _, _, settings, headers, _ = setup(db_session, test_settings)
    with _client(settings, db_session, AssistantProvider(unsafe=True)) as client:
        assert client.post(SEND, headers=headers, json=payload()).status_code == 502
        assert client.get(ROOT, headers=headers).json()["items"] == []
    assert db_session.scalar(select(func.count()).select_from(AIConversationTurn)) == 0


def test_history_is_bounded_and_identifiers_redacted(db_session, test_settings):
    _, _, provider, settings, headers, _ = setup(db_session, test_settings)
    cid = None
    with _client(settings, db_session, provider) as client:
        for index in range(5):
            result = client.post(SEND, headers=headers, json=payload(cid, message=f"Question {index} from person@example.com " + "general health " * 60))
            assert result.status_code == 200, result.text
            cid = result.json()["conversation"]["id"]
        data = json.loads(provider.prompts[-1].split("\n")[-1])
        assert len(data["conversation_history"]) == 3
        assert "person@example.com" not in provider.prompts[-1]
        assert all(len(item["question"]) <= 500 for item in data["conversation_history"])
        assert client.get(ROOT + "?offset=-1", headers=headers).status_code == 422


def test_history_requires_citizen_session_and_works_when_ai_disabled(db_session, test_settings):
    _, _, provider, settings, headers, _ = setup(db_session, test_settings)
    with _client(settings, db_session, provider) as client:
        cid = client.post(SEND, headers=headers, json=payload()).json()["conversation"]["id"]
        for path in (ROOT, f"{ROOT}/{cid}"):
            assert client.get(path).status_code == 401
        assert client.delete(f"{ROOT}/{cid}").status_code == 401
        assert client.post(SEND, json=payload()).status_code == 401
        facility = _facility(db_session)
        user, registration = _professional(db_session, facility)
        professional_headers = _auth(_token(db_session, settings, user, Portal.PROFESSIONAL, role_registration_id=registration.id))
        assert client.get(ROOT, headers=professional_headers).status_code == 403
    with _client(settings.model_copy(update={"ai_enabled": False, "ai_record_context_enabled": False}), db_session, provider) as client:
        assert client.get(f"{ROOT}/{cid}", headers=headers).status_code == 200
        assert client.post(SEND, headers=headers, json=payload(cid)).status_code == 503
        assert client.delete(f"{ROOT}/{cid}", headers=headers).status_code == 204


def test_pagination_and_fifty_turn_cap(db_session, test_settings):
    owner, _, provider, settings, headers, _ = setup(db_session, test_settings)
    with _client(settings, db_session, provider) as client:
        result = client.post(SEND, headers=headers, json=payload()).json()
        cid = uuid.UUID(result["conversation"]["id"])
        db_session.add_all(AIConversation(citizen_id=owner.id, title=f"Private conversation {index}") for index in range(30))
        db_session.add_all(AIConversationTurn(conversation_id=cid, citizen_id=owner.id, request_id=uuid.uuid4(), mode="GENERAL", message="A saved question", response=result["turn"]["response"]) for _ in range(49))
        db_session.commit()
        first = client.get(ROOT, headers=headers).json()
        second = client.get(ROOT + "?offset=30", headers=headers).json()
        assert len(first["items"]) == 30 and first["next_offset"] == 30
        assert len(second["items"]) == 1 and second["next_offset"] is None
        assert not ({item["id"] for item in first["items"]} & {item["id"] for item in second["items"]})
        assert client.post(SEND, headers=headers, json=payload(str(cid))).status_code == 409
        assert len(provider.prompts) == 1


def test_deleted_conversation_cannot_be_resurrected_by_inflight_generation(db_session, test_settings):
    from app.ai.conversation_service import ConversationService
    owner, _, provider, settings, headers, _ = setup(db_session, test_settings)
    with _client(settings, db_session, provider) as client:
        cid = client.post(SEND, headers=headers, json=payload()).json()["conversation"]["id"]
    class DeleteDuringGeneration(AssistantProvider):
        async def generate_structured(self, prompt, response_model):
            ConversationService(db_session).remove(owner.id, uuid.UUID(cid))
            return await super().generate_structured(prompt, response_model)
    with _client(settings, db_session, DeleteDuringGeneration()) as client:
        assert client.post(SEND, headers=headers, json=payload(cid)).status_code == 404
        assert client.get(ROOT, headers=headers).json()["items"] == []
    assert db_session.scalar(select(func.count()).select_from(AIConversationTurn)) == 0


def test_prompt_budget_drops_old_context_before_rejecting_current_question():
    from app.ai.assistant_service import _general_prompt
    history = [{"question": "question " * 55, "answer": "education " * 50} for _ in range(3)]
    prompt = _general_prompt(task="Explain terminology.", user_input="What is a reference range?", history=history, max_characters=3500)
    assert len(prompt) <= 3500
    data = json.loads(prompt.split("\n")[-1])
    assert data["user_input"] == "What is a reference range?"
    assert len(data["conversation_history"]) < 3
