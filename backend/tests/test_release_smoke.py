"""Offline deployment-check contracts; zero external requests."""
import importlib.util
import io
import json
import subprocess
from pathlib import Path
from urllib.error import HTTPError

import pytest

spec = importlib.util.spec_from_file_location("release_smoke", Path(__file__).resolve().parents[2] / "scripts/smoke_release.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
ORIGIN = "https://healthlink-sd.vercel.app"


class Response(io.BytesIO):
    status = 200

    def __init__(self, url, body):
        super().__init__(body)
        self.url = url

    def geturl(self):
        return self.url


@pytest.mark.parametrize("target", ["http://healthlink-sd.vercel.app", "https://example.com", "https://healthlink-sd.vercel.app.evil.test", "https://secret@healthlink-sd.vercel.app", "https://healthlink-sd.vercel.app?token=secret", "https://healthlink-sd.vercel.app/path"])
def test_targets_are_credential_free_vercel_origins(target):
    with pytest.raises(ValueError):
        smoke.validate_target(target)


def test_stable_frontend_health_and_anonymous_denials(monkeypatch):
    seen = []

    def request(req, timeout):
        seen.append(req.full_url)
        assert not req.has_header("Authorization") and req.data is None and timeout == 15
        path = req.full_url[len(ORIGIN):]
        if path in smoke.PROTECTED_PATHS:
            raise HTTPError(req.full_url, 401, "Unauthorized", {}, None)
        body = json.dumps({"status": "healthy", "environment": "production"}).encode() if path == "/health" else b"<title>HealthLink</title>"
        return Response(req.full_url, body)

    monkeypatch.setattr(smoke, "urlopen", request)
    smoke.smoke(ORIGIN, attempts=1)
    assert len(seen) == len(set(seen)) == 9


@pytest.mark.parametrize("path,body", [("/health", b'{"status":"healthy","environment":"test"}'), ("/health", b'[]'), ("/", b"error page"), ("/", b"x" * (smoke.MAX_RESPONSE_BYTES + 1))], ids=["wrong-environment", "invalid-health-shape", "error-page", "oversized-body"])
def test_wrong_environment_error_page_and_oversized_body_fail(monkeypatch, path, body):
    monkeypatch.setattr(smoke, "urlopen", lambda req, timeout: Response(req.full_url, body))
    with pytest.raises(RuntimeError):
        smoke.probe(ORIGIN, path)


def test_redirect_and_unprotected_clinical_endpoint_fail(monkeypatch):
    monkeypatch.setattr(smoke, "urlopen", lambda req, timeout: Response(ORIGIN + "/admin/login", b"<title>HealthLink</title>"))
    with pytest.raises(RuntimeError):
        smoke.probe(ORIGIN, "/")
    monkeypatch.setattr(smoke, "urlopen", lambda req, timeout: Response(req.full_url, b""))
    with pytest.raises(RuntimeError):
        smoke.probe(ORIGIN, smoke.PROTECTED_PATHS[0])


def test_protected_staging_uses_existing_cli_identity_without_secret_arguments(monkeypatch):
    seen = []
    def run(args, **kwargs):
        seen.append(args)
        assert args[:6] == ["vercel", "curl", args[2], "--deployment", ORIGIN, "--scope"]
        assert args[6:8] == ["mahim2077s-projects", "--"]
        assert "--location" not in args and "--token" not in args
        assert "--max-filesize" in args and "--max-time" in args
        assert kwargs == dict(stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=45)
        path = args[2]
        status = 401 if path in smoke.PROTECTED_PATHS else 200
        body = json.dumps({"status": "healthy", "environment": "production"}).encode() if path == "/health" else b"<title>HealthLink</title>"
        return subprocess.CompletedProcess(args, 0, body + f"\nHEALTHLINK_SMOKE_META:{status}:{ORIGIN}{path}".encode())
    monkeypatch.setattr(smoke.subprocess, "run", run)
    smoke.smoke(ORIGIN, attempts=1, vercel_auth=True)
    assert len(seen) == 9


@pytest.mark.parametrize("output", [b"", b"secret-cli-output", b"\nHEALTHLINK_SMOKE_META:bad:url", b"\nHEALTHLINK_SMOKE_META:0:url", b"x" * (smoke.MAX_RESPONSE_BYTES + 1) + f"\nHEALTHLINK_SMOKE_META:200:{ORIGIN}/health".encode()], ids=["empty", "missing-metadata", "bad-status", "zero-status", "oversized"])
def test_authenticated_transport_rejects_malformed_or_oversized_output(monkeypatch, output):
    monkeypatch.setattr(smoke.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, output))
    with pytest.raises(RuntimeError, match="^Authenticated staged smoke transport failed.$"):
        smoke.vercel_response(ORIGIN, "/health")


@pytest.mark.parametrize("error", [OSError("private"), subprocess.TimeoutExpired("vercel", 45), subprocess.CalledProcessError(1, "vercel", stderr="private")])
def test_authenticated_transport_does_not_disclose_cli_errors(monkeypatch, error):
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr(smoke.subprocess, "run", failed)
    with pytest.raises(RuntimeError, match="^Authenticated staged smoke transport failed.$"):
        smoke.vercel_response(ORIGIN, "/health")


def test_authenticated_transport_still_rejects_redirect_or_public_private_endpoint(monkeypatch):
    monkeypatch.setattr(smoke, "vercel_response", lambda *args: (302, ORIGIN + "/health", b""))
    with pytest.raises(RuntimeError):
        smoke.probe(ORIGIN, "/health", vercel_auth=True)
    monkeypatch.setattr(smoke, "vercel_response", lambda *args: (200, ORIGIN + smoke.PROTECTED_PATHS[0], b""))
    with pytest.raises(RuntimeError):
        smoke.probe(ORIGIN, smoke.PROTECTED_PATHS[0], vercel_auth=True)


def test_authenticated_transport_rejects_unknown_path_before_cli(monkeypatch):
    monkeypatch.setattr(smoke.subprocess, "run", lambda *a, **k: pytest.fail("CLI must not run"))
    with pytest.raises(ValueError):
        smoke.vercel_response(ORIGIN, "/unsupported")
