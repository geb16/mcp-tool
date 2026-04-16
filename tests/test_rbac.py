from enterprise_mcp.mcp.common import create_refund_request
from enterprise_mcp.observability.context import role_var, tenant_id_var


def test_write_tool_blocked_for_viewer():
    role_token = role_var.set("viewer")
    tenant_token = tenant_id_var.set("tenant-a")
    try:
        result = create_refund_request(
            order_id="ORD-1002",
            reason="Wrong item delivered",
            approved_by_human=True,
        )
    finally:
        role_var.reset(role_token)
        tenant_id_var.reset(tenant_token)

    assert result["ok"] is False
    assert "cannot execute write tool" in result["message"]
