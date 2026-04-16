from __future__ import annotations

from functools import partial

import anyio
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from enterprise_mcp.config import settings
from enterprise_mcp.logging import get_logger
from enterprise_mcp.trainer.service import run_direct_tool, run_model_chat, snapshot_state
from enterprise_mcp.trainer.ui import TRAINER_HTML

logger = get_logger(__name__)


def _ensure_dev_mode() -> JSONResponse | None:
    if settings.app_env not in {"dev", "test"}:
        return JSONResponse(
            {"error": "Trainer UI is disabled outside dev/test environments."},
            status_code=403,
        )
    return None


async def trainer_page(_request: Request) -> HTMLResponse:
    blocked = _ensure_dev_mode()
    if blocked:
        return HTMLResponse("Trainer UI is disabled outside dev/test environments.", status_code=blocked.status_code)
    return HTMLResponse(TRAINER_HTML)


async def trainer_chat(request: Request) -> JSONResponse:
    blocked = _ensure_dev_mode()
    if blocked:
        return blocked

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)

    message = str(payload.get("message", "")).strip()
    tenant_id = str(payload.get("tenant_id") or settings.default_tenant_id).strip()
    role = str(payload.get("role") or "support_manager").strip().lower()
    openai_api_key = str(payload.get("openai_api_key") or "").strip()

    if not message:
        return JSONResponse({"error": "message is required."}, status_code=400)

    try:
        result = await anyio.to_thread.run_sync(
            partial(
                run_model_chat,
                message=message,
                tenant_id=tenant_id,
                role=role,
                openai_api_key=openai_api_key,
            )
        )
    except Exception:
        logger.exception("trainer chat failed")
        return JSONResponse(
            {"error": "Model call failed. Verify OPENAI_API_KEY and check server logs."},
            status_code=503,
        )

    return JSONResponse({"answer": result.answer, "model": result.model, "tool_trace": result.tool_trace})


async def trainer_state(_request: Request) -> JSONResponse:
    blocked = _ensure_dev_mode()
    if blocked:
        return blocked

    return JSONResponse(snapshot_state())


async def trainer_direct_tool(request: Request) -> JSONResponse:
    blocked = _ensure_dev_mode()
    if blocked:
        return blocked

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON payload."}, status_code=400)

    tool_name = str(payload.get("tool_name", "")).strip()
    arguments = payload.get("arguments") or {}
    tenant_id = str(payload.get("tenant_id") or settings.default_tenant_id).strip()
    role = str(payload.get("role") or "viewer").strip().lower()

    if not tool_name:
        return JSONResponse({"error": "tool_name is required."}, status_code=400)
    if not isinstance(arguments, dict):
        return JSONResponse({"error": "arguments must be an object."}, status_code=400)

    try:
        result = run_direct_tool(
            tool_name=tool_name,
            arguments=arguments,
            tenant_id=tenant_id,
            role=role,
        )
    except Exception:
        logger.exception("trainer direct tool failed")
        return JSONResponse({"error": "Direct tool execution failed."}, status_code=500)

    return JSONResponse({"result": result})
