"""Add citizen-visible clinical access audit metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0028_medical_access_logs"
down_revision = "0027_reminders"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("medical_record_access_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("actor_professional_role_registration_id", sa.Uuid(), sa.ForeignKey("professional_role_registrations.id", ondelete="RESTRICT")),
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("healthcare_facilities.id", ondelete="RESTRICT")),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.Uuid()),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("request_id", sa.String(100)),
        sa.Column("access_source", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_medical_access_citizen_created", "medical_record_access_logs", ["citizen_id", "created_at"])


def downgrade():
    op.drop_table("medical_record_access_logs")
