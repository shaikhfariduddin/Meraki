"""
Seller-side order fulfillment: view orders containing this seller's
products, and move them through the status state machine.

Valid transitions only — cancellation is only allowed early (before
the seller has committed to shipping), and once SHIPPED an order can
only move forward to DELIVERED, never sideways to CANCELLED. Cancelling
returns the reserved stock.
"""
from app.models.order import OrderStatus, OrderStatusHistory
from app.repositories import inventory_repository, seller_order_repository

VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


class SellerOrderNotFound(Exception):
    pass


class InvalidStatusTransition(Exception):
    def __init__(self, current: OrderStatus, requested: OrderStatus):
        super().__init__(f"Cannot move from '{current.value}' to '{requested.value}'")
        self.current = current
        self.requested = requested


def list_for_seller(db, *, seller_profile, status, page, page_size):
    return seller_order_repository.list_for_seller(
        db, seller_profile.id, status=status, page=page, page_size=page_size
    )


def get_for_seller(db, *, seller_profile, seller_order_id):
    seller_order = seller_order_repository.get_for_seller(
        db, seller_profile.id, seller_order_id
    )
    if seller_order is None:
        raise SellerOrderNotFound()
    return seller_order


def update_status(db, *, seller_profile, seller_order_id, new_status, changed_by_user_id):
    seller_order = seller_order_repository.get_for_seller(
        db, seller_profile.id, seller_order_id
    )
    if seller_order is None:
        raise SellerOrderNotFound()

    allowed = VALID_TRANSITIONS.get(seller_order.status, set())
    if new_status not in allowed:
        raise InvalidStatusTransition(seller_order.status, new_status)

    if new_status == OrderStatus.CANCELLED:
        for item in seller_order.items:
            inventory_repository.increment_stock(db, item.product_id, item.quantity)

    seller_order.status = new_status
    db.add(seller_order)
    db.add(
        OrderStatusHistory(
            seller_order_id=seller_order.id,
            status=new_status,
            changed_by_user_id=changed_by_user_id,
        )
    )
    db.commit()
    db.refresh(seller_order)
    return seller_order
