"""Smoke tests for core MCP tool and resource behavior."""

from enterprise_mcp.mcp.common import get_order_status_tool, get_return_policy_resource


def test_tool_smoke_status():
    """Order status tool should return seeded demo order."""
    result = get_order_status_tool("ORD-1001")
    assert result["found"] is True


def test_resource_smoke_policy():
    """Return policy resource should return expected policy text."""
    result = get_return_policy_resource()
    assert "Returns are accepted" in result
