"""Run the real migration against legacy consent rows without private data."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_legacy_scope_upgrade_and_conservative_downgrade():
    path = Path(__file__).parents[1] / "alembic" / "versions" / "0029_access_grant_scopes.py"
    spec = importlib.util.spec_from_file_location("scope_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite+pysqlite://")
    with engine.begin() as connection:
        connection.execute(text("""CREATE TABLE patient_access_grants (id INTEGER PRIMARY KEY,
            access_scope VARCHAR(50) NOT NULL, revoked_at TIMESTAMP, expires_at TIMESTAMP,
            CONSTRAINT ck_patient_access_grants_valid_scope CHECK (access_scope IN ('FULL_RECORD','LIMITED')))"""))
        connection.execute(text("INSERT INTO patient_access_grants (id, access_scope) VALUES (1, 'FULL_RECORD'), (2, 'LIMITED')"))
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
            rows = connection.execute(text("SELECT access_scope, revoked_at FROM patient_access_grants ORDER BY id")).all()
            assert rows[0] == ("FULL_MEDICAL_HISTORY", None)
            assert rows[1][0] == "EMERGENCY_PROFILE_ONLY" and rows[1][1] is not None
            connection.execute(text("INSERT INTO patient_access_grants (id, access_scope) VALUES (3, 'VISITS_ONLY')"))
            module.downgrade()
            rows = connection.execute(text("SELECT access_scope, revoked_at FROM patient_access_grants ORDER BY id")).all()
            assert rows[0] == ("FULL_RECORD", None)
            assert all(scope == "LIMITED" and revoked is not None for scope, revoked in rows[1:])
    engine.dispose()
