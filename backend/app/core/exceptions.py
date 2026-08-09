from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class HealthLinkError(Exception):
    """Base exception for expected application and business-rule failures."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = 400,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.headers = dict(headers) if headers else None


async def healthlink_error_handler(
    _request: Request,
    exception: HealthLinkError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": exception.detail},
        headers=exception.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HealthLinkError, healthlink_error_handler)  # type: ignore[arg-type]
