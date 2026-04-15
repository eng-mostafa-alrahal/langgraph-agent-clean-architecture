"""Maps domain exceptions to HTTP responses — keeps routers exception-free."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException


async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "detail": exc.detail,
            }
        },
    )


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "detail": "An unexpected error occurred.",
            }
        },
    )
