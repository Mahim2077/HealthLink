"""Offline deployment-check contracts; zero external requests."""
import importlib.util
import io
import json
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
