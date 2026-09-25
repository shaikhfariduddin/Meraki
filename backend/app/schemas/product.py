import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    sort_order: int


class ProductCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10_000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    discount_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    brand: str | None = Field(default=None, max_length=255)
    attributes: dict = Field(default_factory=dict)
    initial_stock: int = Field(default=0, ge=0)
    image_urls: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("discount_price")
    @classmethod
    def discount_below_price(cls, v, info):
        price = info.data.get("price")
        if v is not None and price is not None and v >= price:
            raise ValueError("discount_price must be less than price")
        return v


class ProductUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    discount_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    brand: str | None = None
    attributes: dict | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str
    price: Decimal
    discount_price: Decimal | None
    brand: str | None
    attributes: dict
    is_active: bool
    available_stock: int
    images: list[ProductImageOut]
    created_at: datetime
    updated_at: datetime


class StockUpdate(BaseModel):
    available_stock: int = Field(ge=0)
