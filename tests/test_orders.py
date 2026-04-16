"""Domain tests for order lookup and refund creation paths."""

from enterprise_mcp.domain.orders import create_refund, get_order_status
from enterprise_mcp.models import RefundRequest


def test_get_order_status_found():
    """Known order should return found=True with refund metadata."""
    result = get_order_status("ORD-1002")
    assert result["found"] is True
    assert result["refundable"] is True


def test_get_order_status_not_found():
    """Unknown order should return found=False."""
    result = get_order_status("ORD-404")
    assert result["found"] is False


def test_create_refund_requires_human_approval():
    """Refund should be rejected without human approval flag."""
    result = create_refund(
        RefundRequest(
            order_id="ORD-1002",
            reason="Wrong item delivered",
            approved_by_human=False,
        )
    )
    assert result["ok"] is False
    assert "requires human approval" in result["message"]


def test_create_refund_success():
    """Refund should succeed for refundable order with approval."""
    result = create_refund(
        RefundRequest(
            order_id="ORD-1002",
            reason="Wrong item delivered",
            approved_by_human=True,
        )
    )
    assert result["ok"] is True
    assert result["refund_request_id"] == "RR-ORD-1002"
