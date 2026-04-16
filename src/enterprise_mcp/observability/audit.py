from datetime import UTC, datetime

from enterprise_mcp.logging import get_logger
from enterprise_mcp.observability.context import get_request_context
from enterprise_mcp.observability.events import add_tool_event

logger = get_logger("audit")


def audit_tool_call(
    *,
    tool_name: str,
    status: str,
    duration_ms: float,
    arguments: dict[str, object],
    outcome: dict[str, object] | None = None,
) -> None:
    ctx = get_request_context()
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "tool_call",
        "tool_name": tool_name,
        "status": status,
        "duration_ms": round(duration_ms, 3),
        "request_id": ctx.request_id,
        "trace_id": ctx.trace_id,
        "tenant_id": ctx.tenant_id,
        "role": ctx.role,
        "principal": ctx.principal,
        "arguments": arguments,
        "outcome": outcome or {},
    }
    logger.info(
        "tool call",
        extra=event,
    )
    add_tool_event(event)
