"""HTTP security middleware tests for auth and tracing headers."""

from starlette.testclient import TestClient

from enterprise_mcp.mcp.http_server import build_http_app


def test_healthz_no_auth_required():
    """Health endpoint should be public."""
    client = TestClient(build_http_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"


def test_mcp_requires_api_key():
    """MCP endpoint should reject requests without API key."""
    client = TestClient(build_http_app())
    response = client.get("/mcp")
    assert response.status_code == 401


def test_request_and_trace_headers_present():
    """Responses should include request and trace correlation headers."""
    client = TestClient(build_http_app())
    response = client.get("/healthz")
    assert response.headers.get("x-request-id")
    assert response.headers.get("x-trace-id")
