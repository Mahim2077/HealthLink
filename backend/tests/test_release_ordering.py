"""Offline release ordering and stale-run contracts. No external requests."""
import importlib.util
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release_head", ROOT / "scripts/check_release_head.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
SHA = "a" * 40


@pytest.fixture
def release_env(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", "Mahim2077/HealthLink")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")


def test_current_commit_passes_with_fixed_credential_free_remote(release_env, monkeypatch):
    def run(args, **kwargs):
        assert args == ["git", "ls-remote", "--exit-code", guard.REMOTE, "refs/heads/main"]
        assert kwargs == dict(capture_output=True, text=True, check=True, timeout=30)
        return subprocess.CompletedProcess(args, 0, f"{SHA}\trefs/heads/main\n")
    monkeypatch.setattr(guard.subprocess, "run", run)
    guard.check_release_head()


@pytest.mark.parametrize("output", ["", "b" * 40 + "\trefs/heads/main\n", SHA + "\trefs/heads/other\n", f"{SHA}\trefs/heads/main\n{SHA}\trefs/heads/main\n"])
def test_stale_or_ambiguous_remote_fails_closed(release_env, monkeypatch, output):
    monkeypatch.setattr(guard.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, output))
    with pytest.raises(RuntimeError, match="Stale release rejected"):
        guard.check_release_head()


@pytest.mark.parametrize("key,value", [("GITHUB_SHA", "invalid"), ("GITHUB_REF", "refs/heads/other"), ("GITHUB_REPOSITORY", "other/HealthLink")])
def test_wrong_identity_ref_or_sha_never_contacts_remote(release_env, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid release context must fail before contacting a remote")
    monkeypatch.setattr(guard.subprocess, "run", unexpected)
    with pytest.raises(RuntimeError, match="intended HealthLink"):
        guard.check_release_head()


@pytest.mark.parametrize("error", [OSError("private error"), subprocess.TimeoutExpired("git", 30), subprocess.CalledProcessError(1, "git", stderr="private error")])
def test_remote_failure_is_bounded_and_does_not_echo_details(release_env, monkeypatch, error):
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr(guard.subprocess, "run", failed)
    with pytest.raises(RuntimeError, match="^Could not verify the protected release branch head.$"):
        guard.check_release_head()


def test_migration_through_promotion_share_one_non_cancelling_job_lock():
    workflow = (ROOT / ".github/workflows/ci-cd.yml").read_text(encoding="utf-8")
    release = workflow.split("  release-production:\n", 1)[1]
    assert "  migrate-production:\n" not in workflow
    assert "  deploy-production:\n" not in workflow
    assert "group: healthlink-production\n      cancel-in-progress: false" in release
    assert release.count("python scripts/check_release_head.py") == 3
    names = ["Reject stale release before production migration", "Upgrade production database", "Reject stale release before staging", "Stage prebuilt production application", "Smoke-test staged production deployment", "Reject stale release before promotion", "Promote the tested production deployment", "Smoke-test stable production domain after promotion"]
    positions = [release.index(name) for name in names]
    assert positions == sorted(positions)
    assert "--prebuilt --prod --skip-domain" in release
    assert '--token=' not in workflow
    assert 'AI_API_KEY' not in workflow
