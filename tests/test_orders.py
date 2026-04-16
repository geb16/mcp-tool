from enterprise_mcp.domain.orders import create_refund, get_order_status
from enterprise_mcp.models import RefundRequest


def test_get_order_status_found():
    result = get_order_status("ORD-1002")
    assert result["found"] is True
    assert result["refundable"] is True


def test_get_order_status_not_found():
    result = get_order_status("ORD-404")
    assert result["found"] is False


def test_create_refund_requires_human_approval():
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
    result = create_refund(
        RefundRequest(
            order_id="ORD-1002",
            reason="Wrong item delivered",
            approved_by_human=True,
        )
    )
    assert result["ok"] is True
    assert result["refund_request_id"] == "RR-ORD-1002"