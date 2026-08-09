from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import sys

from sqlalchemy.orm import Session


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.admins.provisioning import AdminProvisioningError, create_trusted_admin
from app.core.config import get_settings
from app.db.session import create_database_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a trusted HealthLink administrator. Password is prompted securely."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--super-admin", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = getpass("Admin password (12–128 characters): ")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL must be configured.", file=sys.stderr)
        return 2
    engine = create_database_engine(settings.database_url)
    try:
        with Session(engine, expire_on_commit=False) as session:
            provisioned = create_trusted_admin(
                session,
                email=args.email,
                password=password,
                first_name=args.first_name,
                last_name=args.last_name,
                is_super_admin=args.super_admin,
            )
        print(f"Created trusted admin {provisioned.user.email} ({provisioned.user.id}).")
        return 0
    except AdminProvisioningError as error:
        print(str(error), file=sys.stderr)
        return 2
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
