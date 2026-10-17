"""Read-only post-release probes. Never accepts credentials or calls a model."""
from __future__ import annotations

import argparse
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


PUBLIC_PAGES = ("/", "/citizen/login", "/professional/login", "/admin/login")
PROTECTED_PATHS = (
    "/api/v1/citizens/me/overview",
    "/api/v1/professionals/me/overview",
    "/api/v1/admin/overview",
    "/api/v1/citizens/me/ai/status",
)
MAX_RESPONSE_BYTES = 512_000


def validate_target(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname
            or not parsed.hostname.endswith(".vercel.app") or parsed.port not in (None, 443)
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/")):
        raise ValueError("Smoke targets must be HTTPS Vercel origins without credentials or paths.")
    return url.rstrip("/")


def probe(origin: str, path: str) -> None:
    expected = 401 if path in PROTECTED_PATHS else 200
    request = Request(origin + path, headers={"User-Agent": "HealthLink-release-smoke/1"})
    try:
        with urlopen(request, timeout=15) as response:
            status, final_url = response.status, response.geturl()
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as response:
        status, final_url = response.code, response.geturl()
        body = b""  # Never read or print an error/medical response body.
    if status != expected or final_url != origin + path:
        raise RuntimeError(f"Smoke contract failed for {path}: expected status {expected} without redirect.")
    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"Response exceeded the bounded smoke budget for {path}.")
    if path == "/health":
        payload = json.loads(body)
        if not isinstance(payload, dict) or payload.get("status") != "healthy" or payload.get("environment") != "production":
            raise RuntimeError("Health did not confirm a healthy production process.")
    elif path in PUBLIC_PAGES and (b"<title>" not in body or b"HealthLink" not in body):
        raise RuntimeError(f"Frontend HTML contract failed for {path}.")


def smoke(url: str, attempts: int = 8) -> None:
    origin = validate_target(url)
    for path in ("/health", *PUBLIC_PAGES, *PROTECTED_PATHS):
        for attempt in range(attempts):
            try:
                probe(origin, path)
                break
            except (HTTPError, URLError, RuntimeError, ValueError, TimeoutError):
                if attempt + 1 == attempts:
                    # Avoid echoing server exceptions, response data or credentials.
                    raise RuntimeError(f"Release smoke failed: {origin}{path}") from None
                time.sleep(5)
        print(f"PASS {origin}{path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+", help="Deployment and stable production origins")
    args = parser.parse_args()
    for target in dict.fromkeys(args.urls):
        smoke(target)
