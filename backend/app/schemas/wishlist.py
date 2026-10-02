import uuid
from decimal import Decimal

from pydantic import BaseModel


class WishlistItemAdd(BaseModel):
    product_id: uuid.UUID


class WishlistItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    price: Decimal
    product_is_active: bool
    available_stock: int


class WishlistOut(BaseModel):
    items: list[WishlistItemOut]
