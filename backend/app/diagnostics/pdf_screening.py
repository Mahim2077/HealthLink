import re
import socket
import struct

from app.core.config import Settings
from app.core.exceptions import HealthLinkError


MAX_PDF_BYTES = 3 * 1024 * 1024


def screen_pdf(content: bytes, settings: Settings) -> bool:
    """Validate PDF structure and report whether ClamAV screened the file."""
    if len(content) > MAX_PDF_BYTES:
        raise HealthLinkError("The PDF must be 3 MB or smaller.", status_code=413)
    trailer = re.search(rb"startxref\s+(\d{1,10})\s+%%EOF\s*\Z", content[-1024:])
    if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)\r?\n|%PDF-(?:1\.[0-7]|2\.0)\r", content):
        raise HealthLinkError("Choose a valid PDF report.", status_code=422)
    if trailer is None or not 0 < int(trailer[1]) < len(content):
        raise HealthLinkError("The PDF report is incomplete or invalid.", status_code=422)
    xref = content[int(trailer[1]):int(trailer[1]) + 64]
    if not re.match(rb"xref\s|\d+\s+\d+\s+obj\b", xref):
        raise HealthLinkError("The PDF report is incomplete or invalid.", status_code=422)
    if not settings.diagnostic_clamav_host:
        return False
    try:
        with socket.create_connection((settings.diagnostic_clamav_host, settings.diagnostic_clamav_port), timeout=8) as scanner:
            scanner.sendall(b"zINSTREAM\x00")
            for offset in range(0, len(content), 65536):
                chunk = content[offset:offset + 65536]
                scanner.sendall(struct.pack(">I", len(chunk)) + chunk)
            scanner.sendall(b"\x00" * 4)
            reply = b""
            while b"\x00" not in reply and len(reply) < 1024:
                part = scanner.recv(1024)
                if not part:
                    break
                reply += part
    except OSError as exc:
        raise HealthLinkError("PDF screening is temporarily unavailable.", status_code=503) from exc
    if reply == b"stream: OK\x00":
        return True
    if reply.endswith(b" FOUND\x00"):
        raise HealthLinkError("The PDF did not pass screening.", status_code=422)
    raise HealthLinkError("PDF screening is temporarily unavailable.", status_code=503)
