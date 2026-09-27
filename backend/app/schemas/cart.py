import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=999)


class CartItemQuantityUpdate(BaseModel):
    quantity: int = Field(ge=1, le=999)


class CartItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    product_is_active: bool
    available_stock: int


class CartOut(BaseModel):
    items: list[CartItemOut]
    subtotal: Decimal
    item_count: int
