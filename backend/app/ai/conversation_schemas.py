import uuid
from datetime import UTC, datetime
from pydantic import BaseModel, ConfigDict, field_validator
from app.ai.assistant_schemas import AIChatRequest, AIChatResponse, ChatMode


class ConversationSendRequest(AIChatRequest):
    conversation_id: uuid.UUID | None = None
    client_request_id: uuid.UUID


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc_dates(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ConversationTurn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    mode: ChatMode
    message: str
    response: AIChatResponse
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_dates(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class ConversationDetail(ConversationSummary):
    turns: list[ConversationTurn]


class ConversationPage(BaseModel):
    items: list[ConversationSummary]
    next_offset: int | None


class ConversationSendResponse(BaseModel):
    conversation: ConversationSummary
    turn: ConversationTurn
