from __future__ import annotations

from collections.abc import Mapping

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
            # Medical free text can contain identifiers anywhere. Preserve the
            # field/type/error message, never echo the submitted value.
            error["input"] = "[REDACTED]"
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
