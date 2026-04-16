from starlette.testclient import TestClient
from types import SimpleNamespace

from enterprise_mcp.mcp.http_server import build_http_app


def test_trainer_page_available_in_test_env():
    client = TestClient(build_http_app())
    response = client.get("/trainer")
    assert response.status_code == 200
    assert "MCP Day-1 Lab" in response.text


def test_trainer_state_returns_observability_payload():
    client = TestClient(build_http_app())
    response = client.get("/trainer/api/state")
    assert response.status_code == 200

    payload = response.json()
    assert "metrics" in payload
    assert "has_openai_api_key" in payload
    assert "orders" in payload
    assert "refunds" in payload
    assert "redis_cache_keys" in payload


def test_trainer_chat_runtime_api_key_passed(monkeypatch):
    captured: dict[str, str] = {}

    def fake_run_model_chat(*, message: str, tenant_id: str, role: str, openai_api_key: str = ""):
        captured["message"] = message
        captured["tenant_id"] = tenant_id
        captured["role"] = role
        captured["openai_api_key"] = openai_api_key
        return SimpleNamespace(answer="ok", model="stub", tool_trace=[])

    monkeypatch.setattr("enterprise_mcp.trainer.http.run_model_chat", fake_run_model_chat)
    client = TestClient(build_http_app())

    response = client.post(
        "/trainer/api/chat",
        json={
            "message": "hello",
            "tenant_id": "tenant-a",
            "role": "viewer",
            "openai_api_key": "sk-runtime-key",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "ok"
    assert captured["openai_api_key"] == "sk-runtime-key"


def test_trainer_direct_tool_viewer_blocked_write():
    client = TestClient(build_http_app())

    response = client.post(
        "/trainer/api/direct-tool",
        json={
            "tool_name": "create_refund_request",
            "arguments": {
                "order_id": "ORD-1002",
                "reason": "Wrong item",
                "approved_by_human": True,
            },
            "tenant_id": "tenant-a",
            "role": "viewer",
        },
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["ok"] is False
    assert "cannot execute write tool" in result["message"]
