from pydantic import BaseModel, Field


class Order(BaseModel):
    order_id: str
    status: str
    tracking: str | None = None
    refundable: bool = False
    amount_gbp: float = Field(ge=0)


class RefundRequest(BaseModel):
    order_id: str
    reason: str
    approved_by_human: bool = False