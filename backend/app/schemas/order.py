import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus
from app.models.payment import PaymentStatus


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: int
    list_price: Decimal
    unit_price: Decimal
    line_total: Decimal


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: OrderStatus
    changed_at: datetime


class SellerOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    items: list[OrderItemOut]
    history: list[StatusHistoryOut]


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    status: PaymentStatus
    provider: str
    payment_method: str
    transaction_reference: str
    failure_reason: str | None
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: OrderStatus
    subtotal: Decimal
    discount_total: Decimal
    total_amount: Decimal
    shipping_address: dict
    created_at: datetime
    seller_orders: list[SellerOrderOut]
    payment: PaymentOut | None


class OrderSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: OrderStatus
    total_amount: Decimal
    item_count: int
    created_at: datetime


class OrderListOut(BaseModel):
    items: list[OrderSummaryOut]
    total: int
    page: int
    page_size: int
