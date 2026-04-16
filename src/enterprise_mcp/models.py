"""Shared typed payload models.

The models in this module define validation contracts exchanged between MCP
tools, domain services, and tests.
"""

from pydantic import BaseModel, Field


class Order(BaseModel):
    """Canonical order representation used by service logic."""

    order_id: str
    status: str
    tracking: str | None = None
    refundable: bool = False
    amount_gbp: float = Field(ge=0)


class RefundRequest(BaseModel):
    """Refund request payload for write operations."""

    order_id: str
    reason: str
    approved_by_human: bool = False
