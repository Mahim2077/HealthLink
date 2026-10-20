"""Private citizen AI conversations, separate from clinical records."""
from alembic import op
import sqlalchemy as sa

revision = "0031_ai_conversations"
down_revision = "0030_doctor_locations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("ai_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_ai_conversations_owner_updated", "ai_conversations", ["citizen_id", "updated_at", "id"])
    op.create_table("ai_conversation_turns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("citizen_id", "request_id", name="uq_ai_conversation_turns_owner_request"),
        sa.CheckConstraint("mode IN ('GENERAL', 'RECORD_AWARE')", name=op.f("ck_ai_conversation_turns_valid_mode")))
    op.create_index("ix_ai_conversation_turns_conversation_created", "ai_conversation_turns", ["conversation_id", "created_at", "id"])


def downgrade():
    op.drop_table("ai_conversation_turns")
    op.drop_table("ai_conversations")
