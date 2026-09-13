"""Daily medicine schedules and idempotent in-app notifications."""
from alembic import op
import sqlalchemy as sa

revision = "0027_reminders"
down_revision = "0026_emergency_profiles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("medicine_reminders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("medicine", sa.String(200), nullable=False),
        sa.Column("prescription_item_id", sa.Uuid(), sa.ForeignKey("prescription_items.id", ondelete="SET NULL")),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Dhaka"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("schedule_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name=op.f("ck_medicine_reminders_valid_dates")),
        sa.CheckConstraint("timezone = 'Asia/Dhaka'", name=op.f("ck_medicine_reminders_supported_timezone")),
    )
    op.create_index("ix_medicine_reminders_citizen", "medicine_reminders", ["citizen_id"])
    op.create_table("medicine_reminder_times",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reminder_id", sa.Uuid(), sa.ForeignKey("medicine_reminders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("daily_time", sa.Time(), nullable=False),
        sa.UniqueConstraint("reminder_id", "daily_time", name="uq_medicine_reminder_times_reminder_time"),
    )
    op.create_table("notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("dedupe_key", sa.String(200), nullable=False, unique=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('MEDICINE','APPOINTMENT')", name=op.f("ck_notifications_valid_kind")),
    )
    op.create_index("ix_notifications_citizen_due", "notifications", ["citizen_id", "due_at"])


def downgrade():
    op.drop_table("notifications")
    op.drop_table("medicine_reminder_times")
    op.drop_table("medicine_reminders")
