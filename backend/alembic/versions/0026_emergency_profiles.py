"""Citizen-managed emergency medical profiles."""
from alembic import op
import sqlalchemy as sa

revision = "0026_emergency_profiles"
down_revision = "0025_lab_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "emergency_profiles",
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("allergies", sa.Text()),
        sa.Column("chronic_conditions", sa.Text()),
        sa.Column("current_medications", sa.Text()),
        sa.Column("emergency_contact_name", sa.String(150)),
        sa.Column("emergency_contact_phone", sa.String(32)),
        sa.Column("special_notes", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("emergency_profiles")
