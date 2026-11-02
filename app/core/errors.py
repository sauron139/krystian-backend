"""One error shape for every failure (see docs/API.md):
{"error": {"code", "message", "details"}}"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers


def not_found(resource: str) -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, "not_found", f"{resource} not found")


def conflict(message: str) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, "conflict", message)


def unauthorized(message: str = "Not authenticated") -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED,
        "unauthorized",
        message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def too_many_requests(retry_after: int) -> AppError:
    return AppError(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "rate_limited",
        "Too many requests. Try again later.",
        details={"retry_after_seconds": retry_after},
        headers={"Retry-After": str(retry_after)},
    )


def _body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "rate_limited",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            _body(exc.code, exc.message, exc.details), exc.status_code, headers=exc.headers
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "error")
        return JSONResponse(
            _body(code, str(exc.detail)), exc.status_code, headers=getattr(exc, "headers", None)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"loc": list(e["loc"]), "message": e["msg"], "type": e["type"]} for e in exc.errors()
        ]
        return JSONResponse(
            _body("validation_error", "Request validation failed", {"fields": fields}),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
