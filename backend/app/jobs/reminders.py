"""Run with python -m app.jobs.reminders using server-side database settings."""
import json
from datetime import UTC, datetime

from app.api.v1 import router as _registered_models  # noqa: F401
from app.db.session import get_session_factory
from app.reminders.service import ReminderService


def main():
    with get_session_factory()() as db:
        print(json.dumps(ReminderService(db).run_due_reminders(datetime.now(UTC))))


if __name__ == "__main__":
    main()
