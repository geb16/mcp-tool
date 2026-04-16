"""Portal orchestration services.

This module coordinates customer chat sessions, approval queue workflows,
admin snapshots, and tenant-level agent-role configuration.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from openai import OpenAI
from sqlalchemy import select

from enterprise_mcp.config import settings
from enterprise_mcp.data.cache import cache_client
from enterprise_mcp.data.db import (
    ApprovalRequestRow,
    ChatMessageRow,
    ChatSessionRow,
    OrderRow,
    RefundRequestRow,
    TenantAgentConfigRow,
    session_scope,
)
from enterprise_mcp.mcp.common import create_refund_request, get_order_status_tool
from enterprise_mcp.observability.events import list_tool_events
from enterprise_mcp.observability.metrics import metrics_response
from enterprise_mcp.observability.context import principal_var, role_var, tenant_id_var

MODEL = "gpt-5"
MAX_TURNS = 6
MAX_HISTORY = 20
MAX_HISTORY_PAGE_SIZE = 80

GDPR_NOTICE = (
    "GDPR notice: We process only necessary data for support. "
    "Please avoid sharing sensitive personal data beyond what is needed."
)

CLOSURE_PROMPT = (
    "Is there anything else I can help with? "
    "If not, we will end the chat shortly."
)

CUSTOMER_SYSTEM_PROMPT = (
    "You are an enterprise customer support assistant. "
    "Follow GDPR-compliant language, be polite, and remind users that chats may be recorded for quality and security monitoring. "
    "Never ask customers to approve internal operations. "
    "If a write operation is requested, use the tool and rely on system workflow to escalate for staff approval."
)

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
        "description": "Write action that requires internal staff approval in this customer workflow.",
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
class CustomerChatResult:
    """Customer chat execution result."""

    session_id: str
    answer: str
    model: str
    assistant_message_id: int
    tool_trace: list[dict[str, Any]]


@dataclass(slots=True)
class AdminDecisionResult:
    """Result of an admin approval decision."""

    ok: bool
    approval_id: str
    status: str
    result: dict[str, Any]


def customer_chat(
    *,
    message: str,
    session_id: str,
    tenant_id: str,
    openai_api_key: str = "",
) -> CustomerChatResult:
    """Execute one customer chat turn with tool-calling support.

    Args:
        message: Customer message text.
        session_id: Existing session ID or empty for a new session.
        tenant_id: Tenant identifier.
        openai_api_key: Optional runtime API key override.

    Returns:
        CustomerChatResult with response text, session metadata, and tool trace.

    Raises:
        RuntimeError: If no OpenAI API key is configured.
    """
    api_key = openai_api_key.strip() or settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    resolved_tenant = tenant_id or settings.default_tenant_id
    active_session_id = _get_or_create_session(session_id=session_id, tenant_id=resolved_tenant)
    _save_message(tenant_id=resolved_tenant, session_id=active_session_id, role="user", content=message)

    history = _load_history(tenant_id=resolved_tenant, session_id=active_session_id)
    input_items = [{"role": "system", "content": CUSTOMER_SYSTEM_PROMPT}] + history

    client = OpenAI(api_key=api_key, timeout=25.0, max_retries=0)
    response = client.responses.create(
        model=MODEL,
        input=input_items,
        tools=TOOL_SCHEMAS,
    )

    tool_trace: list[dict[str, Any]] = []

    for _ in range(MAX_TURNS):
        tool_outputs, calls = _collect_customer_tool_outputs(
            response=response,
            tenant_id=resolved_tenant,
            session_id=active_session_id,
        )
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
        answer = "I can help with that. Could you share a bit more detail so I can proceed safely?"

    if any(call.get("approval_queued") for call in tool_trace):
        answer += (
            "\n\nYour request has been queued for enterprise staff approval. "
            "You do not need to take any approval action."
        )

    if _should_attach_gdpr_notice(tenant_id=resolved_tenant, session_id=active_session_id):
        answer += f"\n\n{GDPR_NOTICE}"

    assistant_message_id = _save_message(
        tenant_id=resolved_tenant,
        session_id=active_session_id,
        role="assistant",
        content=answer,
    )
    _touch_session(tenant_id=resolved_tenant, session_id=active_session_id)

    return CustomerChatResult(
        session_id=active_session_id,
        answer=answer,
        model=MODEL,
        assistant_message_id=assistant_message_id,
        tool_trace=tool_trace,
    )


def customer_history(
    *,
    tenant_id: str,
    session_id: str,
    after_id: int = 0,
    limit: int = MAX_HISTORY_PAGE_SIZE,
) -> list[dict[str, Any]]:
    """Return ordered chat history entries for a session.

    Args:
        tenant_id: Tenant identifier.
        session_id: Session identifier.
        after_id: Return only messages with ID greater than this value.
        limit: Maximum number of rows to return.

    Returns:
        Ordered message dictionaries.
    """
    page_size = max(1, min(limit, MAX_HISTORY_PAGE_SIZE))
    with session_scope() as session:
        query = select(ChatMessageRow).where(
            ChatMessageRow.tenant_id == tenant_id,
            ChatMessageRow.session_id == session_id,
        )
        if after_id > 0:
            query = query.where(ChatMessageRow.id > after_id)
        query = query.order_by(ChatMessageRow.id.asc()).limit(page_size)
        rows = session.scalars(query).all()

    return [
        {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def admin_snapshot(*, tenant_id: str) -> dict[str, Any]:
    """Build dashboard snapshot for admin UI.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Metrics lines, recent database rows, cache keys, and audit events.
    """
    payload, _content_type = metrics_response()
    metrics_text = payload.decode("utf-8", errors="replace")

    with session_scope() as session:
        orders = session.scalars(
            select(OrderRow).where(OrderRow.tenant_id == tenant_id).order_by(OrderRow.id.desc()).limit(20)
        ).all()
        refunds = session.scalars(
            select(RefundRequestRow).where(RefundRequestRow.tenant_id == tenant_id).order_by(RefundRequestRow.id.desc()).limit(20)
        ).all()
        approvals = session.scalars(
            select(ApprovalRequestRow)
            .where(ApprovalRequestRow.tenant_id == tenant_id)
            .order_by(ApprovalRequestRow.id.desc())
            .limit(30)
        ).all()
        config = session.scalar(
            select(TenantAgentConfigRow).where(TenantAgentConfigRow.tenant_id == tenant_id)
        )

    redis_keys: list[str] = []
    if cache_client.client:
        try:
            redis_keys = sorted(k for k in cache_client.client.keys("cache:*") if isinstance(k, str))
        except Exception:
            redis_keys = []

    return {
        "metrics": _interesting_metrics(metrics_text),
        "assigned_agent_role": config.assigned_role if config else "support_agent",
        "orders": [_order_to_dict(row) for row in orders],
        "refunds": [_refund_to_dict(row) for row in refunds],
        "approvals": [_approval_to_dict(row) for row in approvals],
        "redis_cache_keys": redis_keys,
        "tool_audit_events": list_tool_events(limit=60),
    }


def set_agent_role(*, tenant_id: str, role: str) -> dict[str, Any]:
    """Persist tenant-specific assigned agent role.

    Args:
        tenant_id: Tenant identifier.
        role: Role to assign.

    Returns:
        Confirmation payload.
    """
    with session_scope() as session:
        config = session.scalar(
            select(TenantAgentConfigRow).where(TenantAgentConfigRow.tenant_id == tenant_id)
        )
        if config is None:
            config = TenantAgentConfigRow(tenant_id=tenant_id, assigned_role=role)
            session.add(config)
        else:
            config.assigned_role = role
            config.updated_at = datetime.now(UTC)

    return {"ok": True, "tenant_id": tenant_id, "assigned_role": role}


def decide_approval(
    *,
    approval_id: str,
    approve: bool,
    decided_by: str,
    executor_role: str,
    decision_note: str = "",
) -> AdminDecisionResult:
    """Apply admin approval decision and optionally execute queued tool call.

    Args:
        approval_id: Approval request identifier.
        approve: Decision flag.
        decided_by: Staff principal identifier.
        executor_role: Role used for actual tool execution.
        decision_note: Optional decision note.

    Returns:
        AdminDecisionResult with final status and execution result.
    """
    with session_scope() as session:
        approval = session.scalar(
            select(ApprovalRequestRow).where(ApprovalRequestRow.approval_id == approval_id)
        )
        if approval is None:
            return AdminDecisionResult(ok=False, approval_id=approval_id, status="not_found", result={})

        if approval.status != "pending":
            return AdminDecisionResult(
                ok=False,
                approval_id=approval_id,
                status="already_decided",
                result=_safe_json_load(approval.execution_result_json),
            )

        if not approve:
            approval.status = "rejected"
            approval.decided_by = decided_by
            approval.decision_note = decision_note
            approval.decided_at = datetime.now(UTC)
            rejection = {"ok": False, "message": "Request rejected by enterprise staff."}
            approval.execution_result_json = json.dumps(rejection)
            _save_message(
                tenant_id=approval.tenant_id,
                session_id=approval.session_id,
                role="assistant",
                content=_build_decision_customer_message(
                    approved=False,
                    tool_name=approval.tool_name,
                    result=rejection,
                    decision_note=decision_note,
                ),
            )
            _touch_session(tenant_id=approval.tenant_id, session_id=approval.session_id)
            return AdminDecisionResult(
                ok=True,
                approval_id=approval_id,
                status="rejected",
                result=rejection,
            )

        arguments = _safe_json_load(approval.arguments_json)
        if approval.tool_name == "create_refund_request":
            arguments["approved_by_human"] = True

        result = _execute_tool_for_tenant(
            tool_name=approval.tool_name,
            arguments=arguments,
            tenant_id=approval.tenant_id,
            role=executor_role,
            principal=f"admin:{decided_by}",
        )

        approval.status = "approved"
        approval.decided_by = decided_by
        approval.decision_note = decision_note
        approval.decided_at = datetime.now(UTC)
        approval.execution_result_json = json.dumps(result)
        _save_message(
            tenant_id=approval.tenant_id,
            session_id=approval.session_id,
            role="assistant",
            content=_build_decision_customer_message(
                approved=True,
                tool_name=approval.tool_name,
                result=result,
                decision_note=decision_note,
            ),
        )
        _touch_session(tenant_id=approval.tenant_id, session_id=approval.session_id)

        return AdminDecisionResult(
            ok=True,
            approval_id=approval_id,
            status="approved",
            result=result,
        )


def _collect_customer_tool_outputs(
    *,
    response,
    tenant_id: str,
    session_id: str,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Process model function-calls for customer workflow.

    Args:
        response: OpenAI response object.
        tenant_id: Tenant identifier.
        session_id: Customer session identifier.

    Returns:
        Tuple of function_call_output items and tool trace entries.
    """
    outputs: list[dict[str, str]] = []
    calls: list[dict[str, Any]] = []

    for item in response.output:
        if _get_value(item, "type") != "function_call":
            continue

        tool_name = str(_get_value(item, "name") or "")
        call_id = str(_get_value(item, "call_id") or "")
        arguments_raw = _get_value(item, "arguments") or "{}"
        arguments = _safe_json_load(arguments_raw)

        if not tool_name or not call_id:
            continue

        if tool_name == "create_refund_request":
            approval = _queue_approval(
                tenant_id=tenant_id,
                session_id=session_id,
                tool_name=tool_name,
                arguments=arguments,
            )
            result = {
                "ok": False,
                "requires_human_approval": True,
                "approval_id": approval.approval_id,
                "message": "Refund request queued for enterprise staff approval.",
            }
            calls.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result,
                    "approval_queued": True,
                }
            )
        else:
            role = _get_agent_role(tenant_id=tenant_id)
            result = _execute_tool_for_tenant(
                tool_name=tool_name,
                arguments=arguments,
                tenant_id=tenant_id,
                role=role,
                principal="agent",
            )
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


def _execute_tool_for_tenant(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    tenant_id: str,
    role: str,
    principal: str,
) -> dict[str, Any]:
    """Execute one MCP tool under explicit tenant/role/principal context."""
    tenant_token = tenant_id_var.set(tenant_id)
    role_token = role_var.set(role)
    principal_token = principal_var.set(principal)

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


def _queue_approval(
    *,
    tenant_id: str,
    session_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> ApprovalRequestRow:
    """Insert a pending approval request row."""
    approval = ApprovalRequestRow(
        approval_id=f"APR-{uuid.uuid4().hex[:10].upper()}",
        tenant_id=tenant_id,
        session_id=session_id,
        tool_name=tool_name,
        arguments_json=json.dumps(arguments),
        status="pending",
        requested_by="agent",
    )
    with session_scope() as session:
        session.add(approval)
    return approval


def _get_or_create_session(*, session_id: str, tenant_id: str) -> str:
    """Resolve an existing session or create a new one."""
    maybe_session = session_id.strip() if session_id else ""
    if maybe_session:
        with session_scope() as session:
            existing = session.scalar(
                select(ChatSessionRow).where(
                    ChatSessionRow.session_id == maybe_session,
                    ChatSessionRow.tenant_id == tenant_id,
                )
            )
            if existing:
                return existing.session_id

    new_session_id = f"SESS-{uuid.uuid4().hex[:12]}"
    with session_scope() as session:
        session.add(
            ChatSessionRow(
                session_id=new_session_id,
                tenant_id=tenant_id,
                assigned_agent_role=_get_agent_role(tenant_id=tenant_id),
            )
        )
    return new_session_id


def _save_message(*, tenant_id: str, session_id: str, role: str, content: str) -> int:
    """Insert a chat message row.

    Returns:
        Inserted message database ID.
    """
    with session_scope() as session:
        row = ChatMessageRow(
            tenant_id=tenant_id,
            session_id=session_id,
            role=role,
            content=content,
        )
        session.add(row)
        session.flush()
        return int(row.id)


def _touch_session(*, tenant_id: str, session_id: str) -> None:
    """Update session ``updated_at`` timestamp."""
    with session_scope() as session:
        session_row = session.scalar(
            select(ChatSessionRow).where(
                ChatSessionRow.tenant_id == tenant_id,
                ChatSessionRow.session_id == session_id,
            )
        )
        if session_row:
            session_row.updated_at = datetime.now(UTC)


def _load_history(*, tenant_id: str, session_id: str) -> list[dict[str, str]]:
    """Load recent user/assistant messages for model context."""
    with session_scope() as session:
        rows = session.scalars(
            select(ChatMessageRow)
            .where(
                ChatMessageRow.tenant_id == tenant_id,
                ChatMessageRow.session_id == session_id,
            )
            .order_by(ChatMessageRow.id.desc())
            .limit(MAX_HISTORY)
        ).all()

    items: list[dict[str, str]] = []
    for row in reversed(rows):
        if row.role not in {"user", "assistant"}:
            continue
        items.append({"role": row.role, "content": row.content})
    return items


def _get_agent_role(*, tenant_id: str) -> str:
    """Return assigned tenant agent role or default role."""
    with session_scope() as session:
        config = session.scalar(
            select(TenantAgentConfigRow).where(TenantAgentConfigRow.tenant_id == tenant_id)
        )
    if config and config.assigned_role:
        return config.assigned_role
    return "support_agent"


def _should_attach_gdpr_notice(*, tenant_id: str, session_id: str) -> bool:
    """Return whether GDPR notice should be appended for this session."""
    with session_scope() as session:
        first_assistant = session.scalar(
            select(ChatMessageRow.id)
            .where(
                ChatMessageRow.tenant_id == tenant_id,
                ChatMessageRow.session_id == session_id,
                ChatMessageRow.role == "assistant",
            )
            .limit(1)
        )
    return first_assistant is None


def _build_decision_customer_message(
    *,
    approved: bool,
    tool_name: str,
    result: dict[str, Any],
    decision_note: str,
) -> str:
    """Build customer-facing message for an admin decision outcome."""
    if approved:
        if result.get("ok") is False:
            reason = str(result.get("message") or "The request could not be completed.")
            summary = (
                "Your request was approved by enterprise staff for processing, "
                f"but it could not be completed. Reason: {reason}"
            )
        elif tool_name == "create_refund_request" and result.get("ok"):
            refund_id = str(result.get("refund_request_id", "")).strip()
            if refund_id:
                summary = (
                    "Your request was approved by enterprise staff. "
                    f"Refund request `{refund_id}` has been created."
                )
            else:
                summary = "Your request was approved by enterprise staff and has been processed."
        else:
            summary = "Your request was approved by enterprise staff."
    else:
        summary = "Your request was reviewed by enterprise staff and was not approved."

    note = f" Staff note: {decision_note.strip()}" if decision_note.strip() else ""
    return f"{summary}{note}\n\n{CLOSURE_PROMPT}"


def _safe_json_load(raw: str | None) -> dict[str, Any]:
    """Parse JSON object safely, returning empty dict on failure."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {}


def _get_value(item: Any, key: str) -> Any:
    """Read value by attribute or dict key from heterogeneous objects."""
    if hasattr(item, key):
        return getattr(item, key)
    if isinstance(item, dict):
        return item.get(key)
    return None


def _interesting_metrics(metrics_text: str) -> list[str]:
    """Filter Prometheus exposition to portal-relevant metric lines."""
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


def _order_to_dict(row: OrderRow) -> dict[str, Any]:
    """Serialize an order row into response dictionary."""
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "order_id": row.order_id,
        "status": row.status,
        "tracking": row.tracking,
        "refundable": row.refundable,
        "amount_gbp": row.amount_gbp,
    }


def _refund_to_dict(row: RefundRequestRow) -> dict[str, Any]:
    """Serialize a refund row into response dictionary."""
    return {
        "id": row.id,
        "refund_request_id": row.refund_request_id,
        "tenant_id": row.tenant_id,
        "order_id": row.order_id,
        "reason": row.reason,
        "approved_by_human": row.approved_by_human,
        "created_at": row.created_at.isoformat(),
    }


def _approval_to_dict(row: ApprovalRequestRow) -> dict[str, Any]:
    """Serialize an approval row into response dictionary."""
    return {
        "approval_id": row.approval_id,
        "tenant_id": row.tenant_id,
        "session_id": row.session_id,
        "tool_name": row.tool_name,
        "arguments": _safe_json_load(row.arguments_json),
        "status": row.status,
        "requested_by": row.requested_by,
        "decision_note": row.decision_note,
        "decided_by": row.decided_by,
        "execution_result": _safe_json_load(row.execution_result_json),
        "created_at": row.created_at.isoformat(),
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }
