"""Replace placeholder consent scopes without widening ambiguous grants.

LIMITED rows are revoked and retained as EMERGENCY_PROFILE_ONLY for audit.
FULL_RECORD has identical read scope to FULL_MEDICAL_HISTORY.
"""
import logging
from alembic import op
import sqlalchemy as sa

revision = "0029_access_grant_scopes"
down_revision = "0028_medical_access_logs"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # Aggregate-only preflight: no citizen identifiers or clinical data in logs.
    rows = connection.execute(sa.text("""SELECT access_scope, COUNT(*) AS total,
        SUM(CASE WHEN revoked_at IS NULL AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP) THEN 1 ELSE 0 END) AS active,
        SUM(CASE WHEN revoked_at IS NOT NULL THEN 1 ELSE 0 END) AS revoked,
        SUM(CASE WHEN expires_at <= CURRENT_TIMESTAMP THEN 1 ELSE 0 END) AS expired
        FROM patient_access_grants GROUP BY access_scope""")).mappings().all()
    logging.getLogger("alembic.runtime.migration").info("Grant scope preflight: %s", [dict(row) for row in rows])
    with op.batch_alter_table("patient_access_grants") as batch:
        batch.drop_constraint(op.f("ck_patient_access_grants_valid_scope"), type_="check")
    connection.execute(sa.text("UPDATE patient_access_grants SET access_scope = 'FULL_MEDICAL_HISTORY' WHERE access_scope = 'FULL_RECORD'"))
    connection.execute(sa.text("UPDATE patient_access_grants SET access_scope = 'EMERGENCY_PROFILE_ONLY', revoked_at = COALESCE(revoked_at, CURRENT_TIMESTAMP) WHERE access_scope = 'LIMITED'"))
    with op.batch_alter_table("patient_access_grants") as batch:
        batch.create_check_constraint(op.f("ck_patient_access_grants_valid_scope"), "access_scope IN ('FULL_MEDICAL_HISTORY','VISITS_ONLY','PRESCRIPTIONS_ONLY','LAB_REPORTS_ONLY','EMERGENCY_PROFILE_ONLY')")


def downgrade():
    with op.batch_alter_table("patient_access_grants") as batch:
        batch.drop_constraint(op.f("ck_patient_access_grants_valid_scope"), type_="check")
    # Older code treated LIMITED as broad; revoke every narrowed grant on rollback.
    op.execute("UPDATE patient_access_grants SET revoked_at = COALESCE(revoked_at, CURRENT_TIMESTAMP) WHERE access_scope != 'FULL_MEDICAL_HISTORY'")
    op.execute("UPDATE patient_access_grants SET access_scope = CASE WHEN access_scope = 'FULL_MEDICAL_HISTORY' THEN 'FULL_RECORD' ELSE 'LIMITED' END")
    with op.batch_alter_table("patient_access_grants") as batch:
        batch.create_check_constraint(op.f("ck_patient_access_grants_valid_scope"), "access_scope IN ('FULL_RECORD','LIMITED')")
