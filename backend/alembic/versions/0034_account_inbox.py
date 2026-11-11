"""Extend existing citizen notices to professional and admin inboxes."""

import sqlalchemy as sa
from alembic import op


revision = "0034_account_inbox"
down_revision = "0033_diagnostic_sessions"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notifications") as table:
        table.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        table.add_column(sa.Column("portal", sa.String(20), nullable=False, server_default="CITIZEN"))
        table.create_foreign_key("fk_notifications_user_id_users", "users", ["user_id"], ["id"], ondelete="RESTRICT")
        table.alter_column("citizen_id", existing_type=sa.Uuid(), nullable=True)
        table.drop_constraint(op.f("ck_notifications_valid_kind"), type_="check")
        table.create_check_constraint(
            op.f("ck_notifications_valid_kind"),
            "kind IN ('MEDICINE','APPOINTMENT','DIAGNOSTIC','VERIFICATION')",
        )
        table.create_check_constraint(
            op.f("ck_notifications_valid_recipient"),
            "(portal = 'CITIZEN' AND citizen_id IS NOT NULL AND user_id IS NULL) OR "
            "(portal IN ('PROFESSIONAL','ADMIN') AND citizen_id IS NULL AND user_id IS NOT NULL)",
        )
        table.create_index("ix_notifications_user_portal_due", ["user_id", "portal", "due_at"])


def downgrade():
    op.execute("DELETE FROM notifications WHERE portal <> 'CITIZEN' OR kind NOT IN ('MEDICINE','APPOINTMENT')")
    with op.batch_alter_table("notifications") as table:
        table.drop_index("ix_notifications_user_portal_due")
        table.drop_constraint(op.f("ck_notifications_valid_recipient"), type_="check")
        table.drop_constraint(op.f("ck_notifications_valid_kind"), type_="check")
        table.create_check_constraint(op.f("ck_notifications_valid_kind"), "kind IN ('MEDICINE','APPOINTMENT')")
        table.alter_column("citizen_id", existing_type=sa.Uuid(), nullable=False)
        table.drop_constraint("fk_notifications_user_id_users", type_="foreignkey")
        table.drop_column("portal")
        table.drop_column("user_id")
