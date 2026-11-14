"""Consistent API error hierarchy and Flask exception handlers."""

from typing import Any

from flask import Flask, g, jsonify
from flask_limiter.errors import RateLimitExceeded
from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Base domain/API exception mapped to structured JSON responses."""

    status_code = 400
    error_code = "bad_request"

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details


class ValidationAPIError(APIError):
    status_code = 400
    error_code = "validation_error"


class NotFoundError(APIError):
    status_code = 404
    error_code = "not_found"


class ConflictError(APIError):
    status_code = 409
    error_code = "conflict"


class UnauthorizedError(APIError):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(APIError):
    status_code = 403
    error_code = "forbidden"


def error_response(
    message: str,
    status_code: int,
    error_code: str,
    details: Any = None,
):
    """Build a uniform JSON error payload including correlation request_id."""
    payload: dict[str, Any] = {
        "error": {
            "code": error_code,
            "message": message,
        },
        "request_id": getattr(g, "request_id", None),
    }
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), status_code


def register_error_handlers(app: Flask) -> None:
    """Register global exception handlers on the Flask application."""

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        if err.status_code >= 500:
            app.logger.error("api_error", extra={"error_code": err.error_code}, exc_info=True)
        return error_response(err.message, err.status_code, err.error_code, err.details)

    @app.errorhandler(MarshmallowValidationError)
    def handle_marshmallow_error(err: MarshmallowValidationError):
        return error_response(
            "Request validation failed.",
            400,
            "validation_error",
            details=err.messages,
        )

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(err: RateLimitExceeded):
        return error_response(
            "Too many requests. Please wait a moment before trying again.",
            429,
            "rate_limit_exceeded",
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        return error_response(
            err.description or err.name,
            err.code or 500,
            err.name.lower().replace(" ", "_"),
        )

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(err: SQLAlchemyError):
        app.logger.exception("database_error", extra={"error_type": type(err).__name__})
        return error_response(
            "A database error occurred while processing your request.",
            500,
            "database_error",
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        app.logger.exception("unhandled_exception", extra={"error_type": type(err).__name__})
        return error_response(
            "An unexpected internal error occurred.",
            500,
            "internal_server_error",
        )
