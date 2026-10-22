"""Offline contracts for reviewed dependency locks and non-bypassable CI gates."""
from pathlib import Path
import re

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]


def locked_requirements(filename: str) -> list[Requirement]:
    content = (ROOT / "backend" / filename).read_text(encoding="utf-8")
    logical = re.sub(r"\\\r?\n\s*", " ", content)
    requirements = []
    for line in logical.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        assert re.search(r"--hash=sha256:[0-9a-f]{64}(?:\s|$)", line), line
        requirement = Requirement(line.split(" --hash=", 1)[0])
        assert not requirement.url
        assert len(requirement.specifier) == 1
        assert next(iter(requirement.specifier)).operator == "=="
        requirements.append(requirement)
    return requirements


def test_runtime_and_development_are_fully_hashed_and_share_runtime_versions():
    runtime = locked_requirements("requirements.txt")
    development = locked_requirements("requirements-dev.txt")
    runtime_pins = {(canonicalize_name(item.name), str(item.specifier)) for item in runtime}
    dev_pins = {(canonicalize_name(item.name), str(item.specifier)) for item in development}
    assert runtime_pins <= dev_pins
    runtime_names = {name for name, _ in runtime_pins}
    assert not {"pytest", "pip-audit", "pip"} & runtime_names
    assert {"pytest", "pip-audit", "pip"} <= {name for name, _ in dev_pins}


def test_security_floors_are_actually_satisfied_by_runtime_lock():
    versions = {canonicalize_name(item.name): next(iter(item.specifier)).version
                for item in locked_requirements("requirements.txt")}
    for floor in ["PyJWT>=2.15.1", "certifi>=2026.10.19", "pillow>=13.0.0",
                  "urllib3>=2.8.0", "Mako>=1.4.2"]:
        requirement = Requirement(floor)
        assert versions[canonicalize_name(requirement.name)] in requirement.specifier


def test_ci_enforces_lock_freshness_hashes_and_both_advisory_gates():
    workflow = (ROOT / ".github/workflows/ci-cd.yml").read_text(encoding="utf-8")
    assert "git diff --exit-code -- backend/requirements.txt backend/requirements-dev.txt" in workflow
    assert "--require-hashes --only-binary=:all: -r backend/requirements-dev.txt" in workflow
    for filename in ["requirements.txt", "requirements-dev.txt"]:
        assert f"pip_audit --strict --disable-pip --require-hashes -s pypi -r backend/{filename}" in workflow
    assert "npm run test:security" in workflow
    assert "npm run audit:security" in workflow
    assert "continue-on-error" not in workflow
    for action in re.findall(r"uses:\s*\S+@(\S+)", workflow):
        assert re.fullmatch(r"[0-9a-f]{40}", action)
    assert workflow.count("persist-credentials: false") == 3
    release = workflow.split("  release-production:\n", 1)[1]
    assert "--require-hashes --only-binary=:all: -r backend/requirements.txt" in release
    assert "requirements-dev.txt" not in release
