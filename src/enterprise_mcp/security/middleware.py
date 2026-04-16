from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from enterprise_mcp.config import settings
from enterprise_mcp.observability.context import (
    principal_var,
    request_id_var,
    role_var,
    tenant_id_var,
    trace_id_var,
)
from enterprise_mcp.observability.metrics import HTTP_REQUEST_COUNT, HTTP_REQUEST_LATENCY, RATE_LIMIT_EVENTS
from enterprise_mcp.security.rate_limit import rate_limiter

OPEN_ENDPOINTS = {"/healthz", "/metrics"}

# 
class RequestSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # call_next is the next middleware or actual request handler
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex

        request_token = request_id_var.set(request_id)
        trace_token = trace_id_var.set(trace_id)
        tenant_token = tenant_id_var.set("")
        role_token = role_var.set("")
        principal_token = principal_var.set("")

        try:
            path = request.url.path
            if not _is_open_endpoint(path):
                auth = self._authenticate(request)
                if auth:
                    response = auth
                    return self._finalize(response, request, start)

            response = await call_next(request)
            return self._finalize(response, request, start)
        finally:
            request_id_var.reset(request_token)
            trace_id_var.reset(trace_token)
            tenant_id_var.reset(tenant_token)
            role_var.reset(role_token)
            principal_var.reset(principal_token)

    def _authenticate(self, request: Request) -> Response | None:
        provided_key = _extract_api_key(request)
        if settings.allowed_api_keys and provided_key not in settings.allowed_api_keys:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        if not settings.allowed_api_keys and settings.app_env in {"prod", "staging"}:
            return JSONResponse({"error": "No API keys configured"}, status_code=500)

        tenant_id = request.headers.get("x-tenant-id", "").strip()
        if not tenant_id:
            if settings.require_tenant_header:
                return JSONResponse({"error": "x-tenant-id header is required"}, status_code=400)
            tenant_id = settings.default_tenant_id

        role = request.headers.get("x-role", "viewer").strip().lower() or "viewer"
        known_roles = settings.read_roles.union(settings.write_roles)
        if role not in known_roles:
            return JSONResponse({"error": f"Role '{role}' is not recognized"}, status_code=403)

        rate_key = f"{tenant_id}:{provided_key}:{request.client.host if request.client else 'na'}"
        if not rate_limiter.allow(rate_key):
            RATE_LIMIT_EVENTS.labels(result="blocked").inc()
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

        RATE_LIMIT_EVENTS.labels(result="allowed").inc()
        tenant_id_var.set(tenant_id)
        role_var.set(role)
        principal_var.set(_principal_name(provided_key))
        return None

    def _finalize(self, response: Response, request: Request, start: float) -> Response:
        response.headers["x-request-id"] = request_id_var.get()
        response.headers["x-trace-id"] = trace_id_var.get()
        elapsed = time.perf_counter() - start
        path = request.url.path
        HTTP_REQUEST_COUNT.labels(method=request.method, path=path, status=str(response.status_code)).inc()
        HTTP_REQUEST_LATENCY.labels(method=request.method, path=path).observe(elapsed)
        return response


def _extract_api_key(request: Request) -> str:
    header_key = request.headers.get("x-api-key", "").strip()
    if header_key:
        return header_key

    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return ""


def _principal_name(api_key: str) -> str:
    if not api_key:
        return "anonymous"
    return f"api_key_***{api_key[-4:]}"


def _is_open_endpoint(path: str) -> bool:
    if path in OPEN_ENDPOINTS:
        return True

    # Training UI routes are intentionally open in dev/test.
    if path.startswith("/trainer"):
        return True

    if path in {"/portal/chat", "/portal/admin"}:
        return True

    return path.startswith("/portal/api/customer/")
