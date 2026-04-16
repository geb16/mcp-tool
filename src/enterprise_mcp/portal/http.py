"""Portal HTTP handlers.

This module exposes customer-facing chat endpoints and admin/staff endpoints
for approvals, tenant agent role assignment, and operational snapshots.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from enterprise_mcp.config import settings
from enterprise_mcp.portal.service import (
    admin_snapshot,
    customer_chat,
    customer_history,
    decide_approval,
    set_agent_role,
)
from enterprise_mcp.portal.ui import ADMIN_HTML, CUSTOMER_HTML


def customer_page(_request: Request) -> HTMLResponse:
    """Serve customer portal UI."""
    return HTMLResponse(CUSTOMER_HTML)


def admin_page(_request: Request) -> HTMLResponse:
    """Serve admin portal UI."""
    return HTMLResponse(ADMIN_HTML)


async def customer_chat_api(request: Request) -> JSONResponse:
    """Process customer chat requests."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)

    message = str(payload.get("message", "")).strip()
    session_id = str(payload.get("session_id") or "").strip()
    tenant_id = str(payload.get("tenant_id") or settings.default_tenant_id).strip()
    openai_api_key = str(payload.get("openai_api_key") or "").strip()

    if not message:
        return JSONResponse({"error": "message is required."}, status_code=400)

    try:
        result = customer_chat(
            message=message,
            session_id=session_id,
            tenant_id=tenant_id,
            openai_api_key=openai_api_key,
        )
    except Exception:
        return JSONResponse(
            {
                "error": "Customer chat failed. Please retry or contact support staff.",
            },
            status_code=503,
        )

    return JSONResponse(
        {
            "session_id": result.session_id,
            "answer": result.answer,
            "model": result.model,
            "assistant_message_id": result.assistant_message_id,
        }
    )


async def customer_history_api(request: Request) -> JSONResponse:
    """Return incremental customer chat history for polling clients."""
    session_id = request.query_params.get("session_id", "").strip()
    tenant_id = request.query_params.get("tenant_id", settings.default_tenant_id).strip()
    after_id_raw = request.query_params.get("after_id", "0").strip()

    if not session_id:
        return JSONResponse({"error": "session_id is required."}, status_code=400)

    try:
        after_id = max(int(after_id_raw), 0)
    except ValueError:
        return JSONResponse({"error": "after_id must be an integer."}, status_code=400)

    messages = customer_history(
        tenant_id=tenant_id,
        session_id=session_id,
        after_id=after_id,
    )
    last_message_id = messages[-1]["id"] if messages else after_id
    return JSONResponse(
        {
            "session_id": session_id,
            "messages": messages,
            "last_message_id": last_message_id,
        }
    )


async def admin_state_api(request: Request) -> JSONResponse:
    """Return admin dashboard state for one tenant."""
    auth_error = _ensure_admin(request)
    if auth_error:
        return auth_error

    tenant_id = request.headers.get("x-tenant-id", settings.default_tenant_id).strip()
    return JSONResponse(admin_snapshot(tenant_id=tenant_id))


async def admin_set_role_api(request: Request) -> JSONResponse:
    """Set tenant-assigned agent role."""
    auth_error = _ensure_admin(request)
    if auth_error:
        return auth_error

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)

    assigned_role = str(payload.get("assigned_role") or "").strip().lower()
    if assigned_role not in settings.read_roles.union(settings.write_roles):
        return JSONResponse({"error": f"Role '{assigned_role}' is not recognized."}, status_code=400)

    tenant_id = request.headers.get("x-tenant-id", settings.default_tenant_id).strip()
    return JSONResponse(set_agent_role(tenant_id=tenant_id, role=assigned_role))


async def admin_decide_approval_api(request: Request) -> JSONResponse:
    """Approve or reject a queued tool approval request."""
    auth_error = _ensure_admin(request)
    if auth_error:
        return auth_error

    approval_id = request.path_params.get("approval_id", "").strip()
    if not approval_id:
        return JSONResponse({"error": "approval_id is required."}, status_code=400)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)

    approve = bool(payload.get("approve", False))
    decision_note = str(payload.get("decision_note") or "").strip()
    decided_by = request.headers.get("x-admin-user", "staff")
    executor_role = request.headers.get("x-role", "admin").strip().lower()
    if executor_role not in settings.read_roles.union(settings.write_roles):
        return JSONResponse({"error": f"Role '{executor_role}' is not recognized."}, status_code=400)

    result = decide_approval(
        approval_id=approval_id,
        approve=approve,
        decided_by=decided_by,
        executor_role=executor_role,
        decision_note=decision_note,
    )

    return JSONResponse(
        {
            "ok": result.ok,
            "approval_id": result.approval_id,
            "status": result.status,
            "result": result.result,
        }
    )


def _ensure_admin(request: Request) -> JSONResponse | None:
    """Validate admin API key header.

    Args:
        request: Incoming request.

    Returns:
        ``None`` when valid, otherwise a 401 response.
    """
    provided = request.headers.get("x-admin-api-key", "").strip()
    if not provided:
        return JSONResponse({"error": "x-admin-api-key header is required."}, status_code=401)

    if provided not in settings.allowed_api_keys:
        return JSONResponse({"error": "Invalid admin API key."}, status_code=401)

    return None
