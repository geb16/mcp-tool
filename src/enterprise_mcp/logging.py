"""Structured logging configuration.

This module configures process-wide JSON logs and enriches each record with
request-scoped observability context.
"""

import json
import logging
import sys
from datetime import UTC, datetime

from enterprise_mcp.config import settings
from enterprise_mcp.observability.context import get_request_context


class JsonFormatter(logging.Formatter):
    """Format log records as JSON payloads."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record into a JSON string.

        Args:
            record: Standard Python log record.

        Returns:
            JSON string containing base fields plus request context.
        """
        ctx = get_request_context()
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app_env": settings.app_env,
            "request_id": ctx.request_id,
            "trace_id": ctx.trace_id,
            "tenant_id": ctx.tenant_id,
            "role": ctx.role,
            "principal": ctx.principal,
        }

        standard_keys = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
        }
        for key, value in record.__dict__.items():
            if key not in standard_keys:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure root logger to emit JSON logs to stderr."""
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Return a module logger.

    Args:
        name: Logger name, usually ``__name__``.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
