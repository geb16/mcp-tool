from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from sqlalchemy import select

from enterprise_mcp.config import settings
from enterprise_mcp.data.cache import cache_client
from enterprise_mcp.data.db import OrderRow, RefundRequestRow, session_scope
from enterprise_mcp.mcp.common import create_refund_request, get_order_status_tool
from enterprise_mcp.observability.context import principal_var, role_var, tenant_id_var
from enterprise_mcp.observability.metrics import metrics_response

MODEL = "gpt-5"
MAX_TURNS = 6

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_order_status_tool",
        "description": "Read-only: returns order status, tracking, amount, and refund eligibility.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "create_refund_request",
        "description": "Write action: create a refund request if order is refundable and approved_by_human is true.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "reason": {"type": "string"},
                "approved_by_human": {"type": "boolean", "default": False},
            },
            "required": ["order_id", "reason"],
            "additionalProperties": False,
        },
    },
]


@dataclass(slots=True)
class ChatResult:
    answer: str
    model: str
    tool_trace: list[dict[str, Any]]


def run_model_chat(*, message: str, tenant_id: str, role: str, openai_api_key: str = "") -> ChatResult:
    api_key = openai_api_key.strip() or settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key, timeout=25.0, max_retries=0)

    response = client.responses.create(
        model=MODEL,
        input=message,
        instructions=(
            "You are an enterprise support copilot. "
            "Use tools when needed. "
            "If a write action fails due to RBAC or approval, explain clearly and suggest next step."
        ),
        tools=TOOL_SCHEMAS,
    )

    tool_trace: list[dict[str, Any]] = []

    for _ in range(MAX_TURNS):
        tool_outputs, calls = _collect_tool_outputs(response, tenant_id=tenant_id, role=role)
        tool_trace.extend(calls)
        if not tool_outputs:
            break

        response = client.responses.create(
            model=MODEL,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=TOOL_SCHEMAS,
        )

    answer = (response.output_text or "").strip()
    if not answer:
        answer = "Model completed without final text. Inspect tool outputs and logs for details."

    return ChatResult(answer=answer, model=MODEL, tool_trace=tool_trace)


def _collect_tool_outputs(
    response, *, tenant_id: str, role: str
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    outputs: list[dict[str, str]] = []
    calls: list[dict[str, Any]] = []

    for item in response.output:
        item_type = _get_value(item, "type")
        if item_type != "function_call":
            continue

        tool_name = _get_value(item, "name")
        call_id = _get_value(item, "call_id")
        args_raw = _get_value(item, "arguments") or "{}"

        if not tool_name or not call_id:
            continue

        try:
            arguments = json.loads(args_raw)
            if not isinstance(arguments, dict):
                arguments = {}
        except json.JSONDecodeError:
            arguments = {}

        result = _execute_local_tool(tool_name, arguments, tenant_id=tenant_id, role=role)
        calls.append(
            {
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
            }
        )
        outputs.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result),
            }
        )

    return outputs, calls


def _execute_local_tool(tool_name: str, arguments: dict[str, Any], *, tenant_id: str, role: str) -> dict[str, Any]:
    tenant_token = tenant_id_var.set(tenant_id)
    role_token = role_var.set(role)
    principal_token = principal_var.set("trainer_ui")

    try:
        if tool_name == "get_order_status_tool":
            return get_order_status_tool(order_id=str(arguments.get("order_id", "")))

        if tool_name == "create_refund_request":
            return create_refund_request(
                order_id=str(arguments.get("order_id", "")),
                reason=str(arguments.get("reason", "")),
                approved_by_human=bool(arguments.get("approved_by_human", False)),
            )

        return {"ok": False, "message": f"Unknown tool: {tool_name}"}
    finally:
        tenant_id_var.reset(tenant_token)
        role_var.reset(role_token)
        principal_var.reset(principal_token)


def run_direct_tool(
    *, tool_name: str, arguments: dict[str, Any], tenant_id: str, role: str
) -> dict[str, Any]:
    return _execute_local_tool(tool_name, arguments, tenant_id=tenant_id, role=role)


def _get_value(item: Any, key: str) -> Any:
    if hasattr(item, key):
        return getattr(item, key)
    if isinstance(item, dict):
        return item.get(key)
    return None


def snapshot_state() -> dict[str, object]:
    payload, _content_type = metrics_response()
    metrics_text = payload.decode("utf-8", errors="replace")

    with session_scope() as session:
        orders = session.scalars(select(OrderRow).order_by(OrderRow.id.desc()).limit(20)).all()
        refunds = session.scalars(select(RefundRequestRow).order_by(RefundRequestRow.id.desc()).limit(20)).all()

    redis_keys: list[str] = []
    if cache_client.client:
        try:
            redis_keys = sorted(k for k in cache_client.client.keys("cache:*") if isinstance(k, str))
        except Exception:
            redis_keys = []

    return {
        "metrics": _interesting_metrics(metrics_text),
        "has_openai_api_key": bool(settings.openai_api_key),
        "orders": [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "order_id": row.order_id,
                "status": row.status,
                "tracking": row.tracking,
                "refundable": row.refundable,
                "amount_gbp": row.amount_gbp,
            }
            for row in orders
        ],
        "refunds": [
            {
                "id": row.id,
                "refund_request_id": row.refund_request_id,
                "tenant_id": row.tenant_id,
                "order_id": row.order_id,
                "reason": row.reason,
                "approved_by_human": row.approved_by_human,
                "created_at": row.created_at.isoformat(),
            }
            for row in refunds
        ],
        "redis_cache_keys": redis_keys,
    }


def _interesting_metrics(metrics_text: str) -> list[str]:
    allowed_prefixes = (
        "mcp_http_requests_total",
        "mcp_http_request_latency_seconds_count",
        "mcp_tool_calls_total",
        "mcp_tool_call_latency_seconds_count",
        "mcp_cache_events_total",
        "mcp_rate_limit_events_total",
    )
    lines = []
    for line in metrics_text.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith(allowed_prefixes):
            lines.append(line)
    return lines
