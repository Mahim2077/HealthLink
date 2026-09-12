"""Structured lab reports and immutable finalized results."""
from alembic import op
import sqlalchemy as sa

revision = "0025_lab_reports"
down_revision = "0024_diagnostic_tests"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lab_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("diagnostic_test_id", sa.Uuid(), sa.ForeignKey("diagnostic_tests.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("healthcare_facilities.id", ondelete="RESTRICT")),
        sa.Column("created_by_role_registration_id", sa.Uuid(), sa.ForeignKey("professional_role_registrations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('DRAFT','FINALIZED')", name=op.f("ck_lab_reports_valid_status")),
        sa.CheckConstraint("(status = 'DRAFT' AND finalized_at IS NULL) OR (status = 'FINALIZED' AND finalized_at IS NOT NULL)", name=op.f("ck_lab_reports_finalization_consistent")),
    )
    op.create_index("ix_lab_reports_citizen_date", "lab_reports", ["citizen_id", "report_date"])
    op.create_table(
        "lab_report_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lab_report_id", sa.Uuid(), sa.ForeignKey("lab_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_name", sa.String(150), nullable=False),
        sa.Column("result_value_text", sa.String(500), nullable=False),
        sa.Column("result_value_numeric", sa.Numeric(18, 6)),
        sa.Column("unit", sa.String(50)),
        sa.Column("reference_range", sa.String(150)),
        sa.Column("flag", sa.String(50)),
    )
    op.create_index("ix_lab_report_items_report", "lab_report_items", ["lab_report_id"])


def downgrade():
    op.drop_table("lab_report_items")
    op.drop_table("lab_reports")
