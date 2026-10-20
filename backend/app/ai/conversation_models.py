"""Private citizen chat history, never part of the clinical record."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (Index("ix_ai_conversations_owner_updated", "citizen_id", "updated_at", "id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIConversationTurn(Base):
    __tablename__ = "ai_conversation_turns"
    __table_args__ = (
        UniqueConstraint("citizen_id", "request_id", name="uq_ai_conversation_turns_owner_request"),
        CheckConstraint("mode IN ('GENERAL', 'RECORD_AWARE')", name="valid_mode"),
        Index("ix_ai_conversation_turns_conversation_created", "conversation_id", "created_at", "id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_conversations.id", ondelete="CASCADE"))
    citizen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("citizen_profiles.id", ondelete="CASCADE"))
    request_id: Mapped[uuid.UUID] = mapped_column()
    mode: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
