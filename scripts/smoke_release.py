"""Read-only release probes. Optional Vercel CLI auth; no app credentials/model calls."""
from __future__ import annotations

import argparse
import json
import subprocess
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


def vercel_response(origin: str, path: str) -> tuple[int, str, bytes]:
    """Use existing CLI authentication; never receive/print a bypass secret."""
    validate_target(origin)
    if path not in ("/health", *PUBLIC_PAGES, *PROTECTED_PATHS):
        raise ValueError("Unsupported authenticated smoke path.")
    marker = b"\nHEALTHLINK_SMOKE_META:"
    try:
        response = subprocess.run(
            ["vercel", "curl", path, "--deployment", origin,
             "--scope", "mahim2077s-projects", "--",
             "--silent", "--max-time", "15", "--max-redirs", "0",
             "--proto", "=https", "--max-filesize", str(MAX_RESPONSE_BYTES),
             "--write-out", marker.decode() + "%{http_code}:%{url_effective}"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, timeout=45,
        )
        body, separator, metadata = response.stdout.rpartition(marker)
        if not separator:
            raise ValueError("Missing response metadata.")
        raw_status, raw_url = metadata.split(b":", 1)
        status, final_url = int(raw_status), raw_url.decode("utf-8")
        if not 100 <= status <= 599:
            raise ValueError("Invalid response status.")
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("Oversized response.")
    except (OSError, subprocess.SubprocessError, ValueError, UnicodeError):
        # CLI stderr may contain protection tokens or server output. Discard it.
        raise RuntimeError("Authenticated staged smoke transport failed.") from None
    return status, final_url, body if status < 400 else b""


def probe(origin: str, path: str, *, vercel_auth: bool = False) -> None:
    expected = 401 if path in PROTECTED_PATHS else 200
    request = Request(origin + path, headers={"User-Agent": "HealthLink-release-smoke/1"})
    if vercel_auth:
        status, final_url, body = vercel_response(origin, path)
    else:
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


def smoke(url: str, attempts: int = 8, *, vercel_auth: bool = False) -> None:
    origin = validate_target(url)
    for path in ("/health", *PUBLIC_PAGES, *PROTECTED_PATHS):
        for attempt in range(attempts):
            try:
                if vercel_auth:
                    probe(origin, path, vercel_auth=True)
                else:
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
    parser.add_argument("--vercel-auth", action="store_true", help="Use existing linked Vercel CLI identity for protected staging")
    args = parser.parse_args()
    for target in dict.fromkeys(args.urls):
        smoke(target, vercel_auth=args.vercel_auth)
