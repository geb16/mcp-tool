from types import SimpleNamespace

from starlette.testclient import TestClient
from sqlalchemy import select

from enterprise_mcp.mcp.http_server import build_http_app
from enterprise_mcp.portal import service
from enterprise_mcp.data.db import ApprovalRequestRow, session_scope


def _admin_headers() -> dict[str, str]:
    return {
        "x-api-key": "test-api-key",
        "x-admin-api-key": "test-api-key",
        "x-role": "admin",
        "x-tenant-id": "tenant-a",
    }


def test_customer_page_loads():
    client = TestClient(build_http_app())
    response = client.get("/portal/chat")
    assert response.status_code == 200
    assert "Enterprise Support" in response.text


def test_customer_chat_api(monkeypatch):
    def fake_customer_chat(*, message: str, session_id: str, tenant_id: str, openai_api_key: str = ""):
        return SimpleNamespace(
            session_id="SESS-test",
            answer=f"echo:{message}",
            model="stub",
            assistant_message_id=7,
            tool_trace=[],
        )

    monkeypatch.setattr("enterprise_mcp.portal.http.customer_chat", fake_customer_chat)
    client = TestClient(build_http_app())

    response = client.post(
        "/portal/api/customer/chat",
        json={"message": "hello", "session_id": "", "tenant_id": "tenant-a"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "SESS-test"
    assert payload["answer"] == "echo:hello"
    assert payload["assistant_message_id"] == 7


def test_customer_history_requires_session_id():
    client = TestClient(build_http_app())
    response = client.get("/portal/api/customer/history")
    assert response.status_code == 400
    assert response.json()["error"] == "session_id is required."


def test_admin_state_requires_auth_headers():
    client = TestClient(build_http_app())
    response = client.get("/portal/api/admin/state")
    assert response.status_code == 401


def test_admin_set_role_success():
    client = TestClient(build_http_app())
    response = client.post(
        "/portal/api/admin/agent-role",
        headers=_admin_headers(),
        json={"assigned_role": "support_manager"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_customer_chat_gdpr_notice_only_once(monkeypatch):
    class _Response:
        def __init__(self, text: str):
            self.id = "resp-1"
            self.output_text = text
            self.output = []

    class _Responses:
        def create(self, **_kwargs):
            return _Response("Support answer")

    class _FakeOpenAI:
        def __init__(self, **_kwargs):
            self.responses = _Responses()

    monkeypatch.setattr("enterprise_mcp.portal.service.OpenAI", _FakeOpenAI)

    first = service.customer_chat(
        message="hi",
        session_id="",
        tenant_id="tenant-a",
        openai_api_key="sk-test",
    )
    second = service.customer_chat(
        message="status update",
        session_id=first.session_id,
        tenant_id="tenant-a",
        openai_api_key="sk-test",
    )

    assert "GDPR notice:" in first.answer
    assert "GDPR notice:" not in second.answer


def test_admin_decision_pushes_customer_update(monkeypatch):
    class _Response:
        def __init__(self, *, text: str, output: list[dict] | None = None):
            self.id = "resp-seq"
            self.output_text = text
            self.output = output or []

    class _Responses:
        def __init__(self):
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return _Response(
                    text="",
                    output=[
                        {
                            "type": "function_call",
                            "name": "create_refund_request",
                            "call_id": "call-1",
                            "arguments": '{"order_id":"ORD-1002","reason":"wrong item"}',
                        }
                    ],
                )
            return _Response(text="Queued for staff review.")

    class _FakeOpenAI:
        def __init__(self, **_kwargs):
            self.responses = _Responses()

    monkeypatch.setattr("enterprise_mcp.portal.service.OpenAI", _FakeOpenAI)

    first = service.customer_chat(
        message="Please refund ORD-1002",
        session_id="",
        tenant_id="tenant-a",
        openai_api_key="sk-test",
    )
    with session_scope() as db:
        approval = db.scalar(
            select(ApprovalRequestRow).where(ApprovalRequestRow.session_id == first.session_id)
        )
        assert approval is not None
        approval_id = approval.approval_id

    decision = service.decide_approval(
        approval_id=approval_id,
        approve=True,
        decided_by="admin1",
        executor_role="support_manager",
        decision_note="Approved by staff",
    )

    assert decision.ok is True
    assert decision.status == "approved"

    updates = service.customer_history(
        tenant_id="tenant-a",
        session_id=first.session_id,
        after_id=first.assistant_message_id,
    )
    assistant_updates = [m for m in updates if m["role"] == "assistant"]
    assert assistant_updates
    assert "approved by enterprise staff" in assistant_updates[-1]["content"].lower()
    assert "Is there anything else I can help with?" in assistant_updates[-1]["content"]


def test_admin_approved_but_execution_rejected_is_clear_to_customer(monkeypatch):
    class _Response:
        def __init__(self, *, text: str, output: list[dict] | None = None):
            self.id = "resp-seq"
            self.output_text = text
            self.output = output or []

    class _Responses:
        def __init__(self):
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return _Response(
                    text="",
                    output=[
                        {
                            "type": "function_call",
                            "name": "create_refund_request",
                            "call_id": "call-1",
                            "arguments": '{"order_id":"ORD-1001","reason":"wrong item"}',
                        }
                    ],
                )
            return _Response(text="Queued for staff review.")

    class _FakeOpenAI:
        def __init__(self, **_kwargs):
            self.responses = _Responses()

    monkeypatch.setattr("enterprise_mcp.portal.service.OpenAI", _FakeOpenAI)

    first = service.customer_chat(
        message="Please refund ORD-1001",
        session_id="",
        tenant_id="tenant-a",
        openai_api_key="sk-test",
    )
    with session_scope() as db:
        approval = db.scalar(
            select(ApprovalRequestRow).where(ApprovalRequestRow.session_id == first.session_id)
        )
        assert approval is not None
        approval_id = approval.approval_id

    decision = service.decide_approval(
        approval_id=approval_id,
        approve=True,
        decided_by="admin1",
        executor_role="support_manager",
        decision_note="Approved by staff",
    )
    assert decision.ok is True
    assert decision.status == "approved"
    assert decision.result.get("ok") is False

    updates = service.customer_history(
        tenant_id="tenant-a",
        session_id=first.session_id,
        after_id=first.assistant_message_id,
    )
    assistant_updates = [m for m in updates if m["role"] == "assistant"]
    assert assistant_updates
    text = assistant_updates[-1]["content"]
    assert "approved by enterprise staff for processing" in text.lower()
    assert "could not be completed" in text.lower()
    assert "order is not eligible for refund" in text.lower()
