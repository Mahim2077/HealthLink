import uuid
from datetime import UTC, datetime
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.ai.assistant_service import AIAssistantService
from app.ai.conversation_models import AIConversation, AIConversationTurn
from app.ai.conversation_schemas import ConversationDetail, ConversationPage, ConversationSendRequest, ConversationSendResponse, ConversationSummary, ConversationTurn
from app.ai.context import sanitize_clinical_text
from app.citizens.dependencies import CitizenContext
from app.core.exceptions import HealthLinkError


class ConversationService:
    def __init__(self, db: Session):
        self.db = db

    def owned(self, owner: uuid.UUID, conversation_id: uuid.UUID, *, lock=False) -> AIConversation:
        query = select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.citizen_id == owner)
        if lock:
            query = query.with_for_update()
        conversation = self.db.scalar(query)
        if conversation is None:
            raise HealthLinkError("Conversation not found.", status_code=404)
        return conversation

    def turns(self, conversation_id: uuid.UUID) -> list[AIConversationTurn]:
        return list(self.db.scalars(select(AIConversationTurn).where(AIConversationTurn.conversation_id == conversation_id).order_by(AIConversationTurn.created_at, AIConversationTurn.id)))

    def list(self, owner: uuid.UUID, offset: int) -> ConversationPage:
        items = list(self.db.scalars(select(AIConversation).where(AIConversation.citizen_id == owner).order_by(AIConversation.updated_at.desc(), AIConversation.id.desc()).offset(offset).limit(31)))
        return ConversationPage(items=[ConversationSummary.model_validate(item) for item in items[:30]], next_offset=offset + 30 if len(items) > 30 else None)

    def detail(self, owner: uuid.UUID, conversation_id: uuid.UUID) -> ConversationDetail:
        conversation = self.owned(owner, conversation_id)
        return ConversationDetail(**ConversationSummary.model_validate(conversation).model_dump(), turns=[ConversationTurn.model_validate(item) for item in self.turns(conversation.id)])

    def remove(self, owner: uuid.UUID, conversation_id: uuid.UUID) -> None:
        conversation = self.owned(owner, conversation_id, lock=True)
        self.db.execute(delete(AIConversationTurn).where(AIConversationTurn.conversation_id == conversation.id))
        self.db.delete(conversation)
        self.db.commit()

    def _replay(self, owner, request: ConversationSendRequest) -> ConversationSendResponse | None:
        turn = self.db.scalar(select(AIConversationTurn).where(AIConversationTurn.citizen_id == owner, AIConversationTurn.request_id == request.client_request_id))
        if turn is None:
            return None
        if (request.conversation_id is not None and turn.conversation_id != request.conversation_id) or turn.message != request.message or turn.mode != request.mode:
            raise HealthLinkError("This request identifier has already been used.", status_code=409)
        return ConversationSendResponse(conversation=ConversationSummary.model_validate(self.owned(owner, turn.conversation_id)), turn=ConversationTurn.model_validate(turn))

    async def send(self, *, citizen: CitizenContext, request: ConversationSendRequest, assistant: AIAssistantService, request_id: str | None) -> ConversationSendResponse:
        owner = citizen.profile.id
        conversation = self.owned(owner, request.conversation_id) if request.conversation_id else None
        replay = self._replay(owner, request)
        if replay:
            return replay
        turns = self.turns(conversation.id) if conversation else []
        if len(turns) >= 50:
            raise HealthLinkError("This conversation is full. Start a new conversation to continue.", status_code=409)
        # General must not resend records or later follow-ups referring to them.
        history = []
        if request.mode == "RECORD_AWARE" or not any(turn.mode == "RECORD_AWARE" for turn in turns):
            terms = (citizen.profile.user.first_name, citizen.profile.user.last_name, citizen.profile.user.email)
            for turn in turns[-3:]:
                history.append({"question": sanitize_clinical_text(turn.message, limit=500, redact_terms=terms), "answer": sanitize_clinical_text(turn.response["answer"], limit=500, redact_terms=terms)})
        response = await assistant.chat(citizen=citizen, request=request, request_id=request_id, history=history)
        if conversation is not None:
            # Record-read auditing commits independently. Reauthorize and lock
            # after generation so concurrent deletion cannot resurrect a chat,
            # and concurrent sends cannot bypass the turn cap or duplicate saves.
            conversation = self.owned(owner, conversation.id, lock=True)
            replay = self._replay(owner, request)
            if replay:
                return replay
            if len(self.turns(conversation.id)) >= 50:
                raise HealthLinkError("This conversation is full. Start a new conversation to continue.", status_code=409)
        now = datetime.now(UTC)
        if conversation is None:
            conversation = AIConversation(citizen_id=owner, title=request.message[:80], created_at=now, updated_at=now)
            self.db.add(conversation)
            self.db.flush()
        conversation.updated_at = now
        turn = AIConversationTurn(conversation_id=conversation.id, citizen_id=owner, request_id=request.client_request_id, mode=request.mode, message=request.message, response=response.model_dump(mode="json"), created_at=now)
        self.db.add(turn)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            replay = self._replay(owner, request)
            if replay:
                return replay
            raise
        return ConversationSendResponse(conversation=ConversationSummary.model_validate(conversation), turn=ConversationTurn.model_validate(turn))
