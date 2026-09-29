"""
Multi-vendor order model.

    Order              one per checkout: one customer, one payment
      └─ SellerOrder   one per seller involved: the unit a seller fulfils
           ├─ OrderItem            what was bought (price frozen at purchase)
           └─ OrderStatusHistory   audit trail of that seller order's status

Why sub-orders instead of just a seller_id on each item? A seller must be
able to move *their* part of an order through PROCESSING -> SHIPPED without
touching another seller's part of the same checkout. Status therefore lives
on SellerOrder; the customer-facing Order.status is derived from it.
"""
import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


_PROGRESS_RANK = {
    OrderStatus.PLACED: 0,
    OrderStatus.CONFIRMED: 1,
    OrderStatus.PROCESSING: 2,
    OrderStatus.SHIPPED: 3,
    OrderStatus.DELIVERED: 4,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("total_amount >= 0", name="ck_orders_total_nonneg"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # A snapshot, not a foreign key: editing or deleting an address later must
    # never rewrite where a historical order was shipped.
    shipping_address: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    seller_orders: Mapped[list["SellerOrder"]] = relationship(
        "SellerOrder", order_by="SellerOrder.created_at", viewonly=True
    )
    payment: Mapped["Payment"] = relationship("Payment", uselist=False, viewonly=True)

    @property
    def status(self) -> OrderStatus:
        """
        Derived, never stored (so it can't drift out of sync): cancelled parts
        are ignored, and the order is only as advanced as its slowest live part.
        """
        statuses = [so.status for so in self.seller_orders]
        if not statuses:
            return OrderStatus.PLACED
        live = [s for s in statuses if s != OrderStatus.CANCELLED]
        if not live:
            return OrderStatus.CANCELLED
        return min(live, key=lambda s: _PROGRESS_RANK[s])

    @property
    def item_count(self) -> int:
        return sum(item.quantity for so in self.seller_orders for item in so.items)


class SellerOrder(Base):
    __tablename__ = "seller_orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("seller_profiles.id"), nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.PLACED
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", order_by="OrderItem.product_name", viewonly=True
    )
    history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory", order_by="OrderStatusHistory.changed_at", viewonly=True
    )
    order: Mapped["Order"] = relationship("Order", viewonly=True)

    @property
    def shipping_address(self) -> dict:
        return self.order.shipping_address if self.order else {}


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    seller_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("seller_orders.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id"), nullable=False, index=True
    )
    # Snapshots taken at purchase time. History never reads the live Product.
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    list_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    seller_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("seller_orders.id"), nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False
    )
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
