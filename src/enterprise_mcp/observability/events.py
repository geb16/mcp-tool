"""In-memory audit event store.

The store is intentionally bounded and thread-safe to support lightweight
admin/trainer inspection without external dependencies.
"""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

_MAX_EVENTS = 500
_event_lock = Lock()
_tool_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)


def add_tool_event(event: dict[str, Any]) -> None:
    """Append an event to the bounded event buffer.

    Args:
        event: Structured audit event payload.
    """
    with _event_lock:
        _tool_events.appendleft(event)


def list_tool_events(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent audit events.

    Args:
        limit: Maximum number of events to return.

    Returns:
        List of most recent events, newest first.
    """
    safe_limit = max(1, min(limit, _MAX_EVENTS))
    with _event_lock:
        return list(_tool_events)[:safe_limit]
