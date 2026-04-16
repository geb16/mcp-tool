"""Tenant isolation tests for domain data access."""

from enterprise_mcp.domain.orders import get_order_status
from enterprise_mcp.observability.context import tenant_id_var


def test_tenant_isolation_returns_not_found_for_other_tenant():
    """Cross-tenant order lookup should not return another tenant's data."""
    token = tenant_id_var.set("tenant-b")
    try:
        result = get_order_status("ORD-1002")
    finally:
        tenant_id_var.reset(token)

    assert result["found"] is False
