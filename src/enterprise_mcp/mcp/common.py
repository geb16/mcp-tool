# this file defines the MCP tools and resources, and the core logic for executing them with observability and access control. The actual business logic for each tool should be implemented in the domain layer (e.g. enterprise_mcp.domain.orders) and imported here.
from __future__ import annotations

import time

from mcp.server.fastmcp import FastMCP

from enterprise_mcp.config import settings
from enterprise_mcp.data.cache import cache_client
from enterprise_mcp.domain.orders import create_refund, get_order_status, get_return_policy
from enterprise_mcp.models import RefundRequest
from enterprise_mcp.observability.audit import audit_tool_call
from enterprise_mcp.observability.metrics import CACHE_EVENTS, TOOL_CALL_COUNT, track_tool_latency
from enterprise_mcp.security.context import current_tenant_id
from enterprise_mcp.security.rbac import AuthorizationError, ensure_tool_access

mcp = FastMCP(
    "enterprise-support-tools",
    json_response=True,
    host=settings.mcp_http_host,
    port=settings.mcp_http_port,
    stateless_http=True,
)


def _cache_key(tool_name: str, *parts: str) -> str:
    tenant_id = current_tenant_id(settings.default_tenant_id)
    encoded_parts = ":".join(parts)
    return f"cache:{tool_name}:{tenant_id}:{encoded_parts}"

# Execute a tool with observability and access control
# This function centralizes the common patterns of:
# - Checking RBAC permissions for the tool
# - Tracking tool call latency and count with Prometheus metrics
# - Auditing tool calls with details like arguments, outcome, duration, and status

def _execute_tool(
    *,
    tool_name: str,
    write: bool,
    arguments: dict[str, object],
    fn,
) -> dict:
    start = time.perf_counter()
    status = "success"
    outcome: dict[str, object] | None = None

    try:
        ensure_tool_access(tool_name=tool_name, write=write)
        with track_tool_latency(tool_name):
            result = fn()
        if isinstance(result, dict) and result.get("ok") is False:
            status = "rejected"
        outcome = result if isinstance(result, dict) else None
        TOOL_CALL_COUNT.labels(tool=tool_name, status=status).inc()
        return result
    except AuthorizationError as exc:
        status = "forbidden"
        TOOL_CALL_COUNT.labels(tool=tool_name, status=status).inc()
        return {"ok": False, "message": str(exc)}
    except Exception as exc:
        status = "error"
        TOOL_CALL_COUNT.labels(tool=tool_name, status=status).inc()
        return {"ok": False, "message": f"Unexpected tool failure: {exc}"}
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0 
        audit_tool_call(
            tool_name=tool_name,
            status=status,
            duration_ms=duration_ms,
            arguments=arguments,
            outcome=outcome,
        )


@mcp.tool()
def get_order_status_tool(order_id: str) -> dict:
    """Read-only: get the current order status, tracking, and refund eligibility."""

    def _resolve() -> dict:
        key = _cache_key("get_order_status_tool", order_id)
        cached = cache_client.get_json(key)
        if cached is not None:
            CACHE_EVENTS.labels(tool="get_order_status_tool", event="hit").inc()
            return cached

        CACHE_EVENTS.labels(tool="get_order_status_tool", event="miss").inc()
        result = get_order_status(order_id)
        cache_client.set_json(key, result)
        return result

    return _execute_tool(
        tool_name="get_order_status_tool",
        write=False,
        arguments={"order_id": order_id},
        fn=_resolve,
    )


@mcp.tool()
def create_refund_request(order_id: str, reason: str, approved_by_human: bool = False) -> dict:
    """Write action: create a refund request. This should require approval in the client."""

    def _resolve() -> dict:
        if not settings.orders_write_enabled:
            return {"ok": False, "message": "Write tools are disabled in this environment."}

        result = create_refund(
            RefundRequest(
                order_id=order_id,
                reason=reason,
                approved_by_human=approved_by_human,
            )
        )

        if result.get("ok"):
            cache_client.delete(_cache_key("get_order_status_tool", order_id))

        return result

    return _execute_tool(
        tool_name="create_refund_request",
        write=True,
        arguments={
            "order_id": order_id,
            "reason": reason,
            "approved_by_human": approved_by_human,
        },
        fn=_resolve,
    )


@mcp.resource("policy://returns")
def get_return_policy_resource() -> str:
    """Read-only company return policy."""
    key = _cache_key("get_return_policy_resource", "policy")
    cached = cache_client.get_json(key)
    if cached is not None:
        CACHE_EVENTS.labels(tool="get_return_policy_resource", event="hit").inc()
        return str(cached.get("value", ""))

    CACHE_EVENTS.labels(tool="get_return_policy_resource", event="miss").inc()
    result = get_return_policy()
    cache_client.set_json(key, {"value": result})
    return result
