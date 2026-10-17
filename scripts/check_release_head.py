"""Reject stale HealthLink releases without credentials or production writes."""
from __future__ import annotations

import os
import re
import subprocess


REPOSITORY = "Mahim2077/HealthLink"
REMOTE = f"https://github.com/{REPOSITORY}.git"


def check_release_head() -> None:
    intended = os.environ.get("GITHUB_SHA", "")
    if (os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or not re.fullmatch(r"[0-9a-f]{40}", intended)):
        raise RuntimeError("Release requires the intended HealthLink main commit.")
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--exit-code", REMOTE, "refs/heads/main"],
            capture_output=True, text=True, check=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        raise RuntimeError("Could not verify the protected release branch head.") from None
    rows = result.stdout.strip().splitlines()
    if len(rows) != 1 or rows[0].split() != [intended, "refs/heads/main"]:
        raise RuntimeError("Stale release rejected: main no longer matches this run.")


if __name__ == "__main__":
    try:
        check_release_head()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    print("PASS: intended HealthLink main commit is current.")
