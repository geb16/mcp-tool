from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any

_MAX_EVENTS = 500
_event_lock = Lock()
_tool_events: deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)


def add_tool_event(event: dict[str, Any]) -> None:
    with _event_lock:
        _tool_events.appendleft(event)


def list_tool_events(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, _MAX_EVENTS))
    with _event_lock:
        return list(_tool_events)[:safe_limit]
