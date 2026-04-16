from __future__ import annotations

from sqlalchemy import func, select

from enterprise_mcp.config import settings
from enterprise_mcp.data.db import OrderRow, RefundRequestRow, session_scope
from enterprise_mcp.models import RefundRequest
from enterprise_mcp.security.context import current_tenant_id


def _tenant_id() -> str:
    return current_tenant_id(settings.default_tenant_id)


def get_order(order_id: str) -> OrderRow | None:
    tenant_id = _tenant_id()
    with session_scope() as session:
        return session.scalar(
            select(OrderRow).where(OrderRow.tenant_id == tenant_id, OrderRow.order_id == order_id)
        )


def get_order_status(order_id: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"found": False, "message": f"Order {order_id} not found."}

    return {
        "found": True,
        "order_id": order.order_id,
        "status": order.status,
        "tracking": order.tracking,
        "refundable": order.refundable,
        "amount_gbp": order.amount_gbp,
    }


def create_refund(refund: RefundRequest) -> dict:
    tenant_id = _tenant_id()

    with session_scope() as session:
        order = session.scalar(
            select(OrderRow).where(
                OrderRow.tenant_id == tenant_id,
                OrderRow.order_id == refund.order_id,
            )
        )
        if not order:
            return {"ok": False, "message": f"Order {refund.order_id} not found."}

        if not order.refundable:
            return {
                "ok": False,
                "order_id": refund.order_id,
                "message": "Order is not eligible for refund.",
            }

        if not refund.approved_by_human:
            return {
                "ok": False,
                "order_id": refund.order_id,
                "message": "Refund requires human approval.",
            }

        refund_request_id = f"RR-{refund.order_id}"
        duplicate = session.scalar(
            select(RefundRequestRow.id).where(
                RefundRequestRow.tenant_id == tenant_id,
                RefundRequestRow.refund_request_id == refund_request_id,
            )
        )
        if duplicate:
            duplicate_count = session.scalar(
                select(func.count(RefundRequestRow.id)).where(
                    RefundRequestRow.tenant_id == tenant_id,
                    RefundRequestRow.order_id == refund.order_id,
                )
            )
            refund_request_id = f"RR-{refund.order_id}-{int(duplicate_count or 0) + 1}"

        order.refundable = False # Mark the order as no longer refundable once a refund request is created

        session.add(
            RefundRequestRow(
                refund_request_id=refund_request_id,
                tenant_id=tenant_id,
                order_id=refund.order_id,
                reason=refund.reason,
                approved_by_human=refund.approved_by_human,
            )
        )

    return {
        "ok": True,
        "order_id": refund.order_id,
        "refund_request_id": refund_request_id,
        "reason": refund.reason,
        "message": "Refund request created successfully.",
    }


def get_return_policy() -> str:
    return (
        "Returns are accepted within 30 days of delivery. "
        "Opened but unused items are eligible. "
        "Refunds are returned to the original payment method within 5-7 business days."
    )
