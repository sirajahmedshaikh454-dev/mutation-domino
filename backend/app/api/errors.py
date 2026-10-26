from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.domain.errors import DomainError

logger = get_logger(__name__)


def _payload(code: str, message: str, details: dict | None = None, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        return _payload(exc.code, exc.message, exc.details, exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "location": ".".join(str(part) for part in error.get("loc", [])),
                "message": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
            }
            for error in exc.errors()
        ]
        return _payload(
            "INVALID_REQUEST",
            "The request body or query parameters are invalid.",
            {"errors": errors},
            422,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", type(exc).__name__)
        return _payload(
            "INTERNAL_ERROR",
            "An unexpected server error occurred. No traceback is exposed.",
            {},
            500,
        )
