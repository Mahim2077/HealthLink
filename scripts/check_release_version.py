"""Print the release version after validating the backend and frontend metadata."""

import json
import re
import runpy
from pathlib import Path


def release_version(root: Path) -> str:
    backend_version = runpy.run_path(str(root / "backend/app/__init__.py")).get("__version__")
    package = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "frontend/package-lock.json").read_text(encoding="utf-8"))
    part = r"(?:0|[1-9][0-9]*)"
    if not isinstance(backend_version, str) or not re.fullmatch(rf"{part}\.{part}\.{part}", backend_version):
        raise ValueError("The HealthLink release version must use MAJOR.MINOR.PATCH.")
    versions = (package.get("version"), lock.get("version"), lock["packages"][""].get("version"))
    if any(version != backend_version for version in versions):
        raise ValueError("The frontend package, lockfile, and API release versions must match.")
    return backend_version


if __name__ == "__main__":
    try:
        print(release_version(Path(__file__).resolve().parents[1]))
    except ValueError as error:
        raise SystemExit(str(error)) from None
