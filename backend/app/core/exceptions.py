from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
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


_SENSITIVE_INPUT_FIELDS = {
    "password",
    "access_token",
    "refresh_token",
    "nid_number",
    "birth_certificate_number",
}


def _redact_sensitive_input(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if str(key).lower() in _SENSITIVE_INPUT_FIELDS
                else _redact_sensitive_input(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_sensitive_input(item) for item in value]
    return value


async def healthlink_error_handler(
    _request: Request,
    exception: HealthLinkError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": exception.detail},
        headers=exception.headers,
    )


async def validation_error_handler(
    _request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    errors = exception.errors()
    for error in errors:
        if "input" in error:
            location = {str(segment).lower() for segment in error.get("loc", ())}
            error["input"] = (
                "[REDACTED]"
                if location & _SENSITIVE_INPUT_FIELDS
                else _redact_sensitive_input(error["input"])
            )
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(errors)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HealthLinkError, healthlink_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(  # type: ignore[arg-type]
        RequestValidationError,
        validation_error_handler,
    )
