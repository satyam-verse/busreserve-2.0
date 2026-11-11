"""Structured JSON logging and per-request correlation ID middleware."""

import json
import logging
import sys
import time
import uuid
from datetime import UTC, datetime

from flask import Flask, g, has_request_context, request


class JsonLogFormatter(logging.Formatter):
    """Render Python log records as single-line JSON objects."""

    RESERVED_ATTRS = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if has_request_context():
            payload["request_id"] = getattr(g, "request_id", None)
            payload["method"] = request.method
            payload["path"] = request.path

        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(app: Flask) -> None:
    """Configure structured JSON logging and request lifecycle hooks."""
    level_name = app.config.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    app.logger.handlers.clear()
    app.logger.propagate = True
    app.logger.setLevel(log_level)

    # Keep Werkzeug request logs clean in dev/testing without losing startup errors
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    @app.before_request
    def _assign_request_context() -> None:
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        g.request_id = incoming_id[:64] if incoming_id else str(uuid.uuid4())
        g.request_start_time = time.perf_counter()

    @app.after_request
    def _log_request_completed(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id

        start_time = getattr(g, "request_start_time", None)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2) if start_time else None

        app.logger.info(
            "http_request",
            extra={
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
                "query_string": request.query_string.decode("utf-8", errors="ignore") or None,
            },
        )
        return response
