"""
Checkout: turns a cart into an order, atomically.

Everything that writes happens inside ONE database transaction:

    1. read + validate (address ownership, products active, sellers approved,
       enough stock) and compute authoritative prices from the database
    2. take stock with atomic conditional UPDATEs        (can fail: oversell)
    3. create Order / SellerOrders / OrderItems / status history
    4. charge the payment provider                       (can fail: declined)
    5. record the payment, empty the cart, COMMIT

If anything fails before step 5's commit, the transaction rolls back and it is
as if checkout never started: stock is untouched, no order exists, the cart is
intact. The one thing a rollback cannot undo is a successful charge at an
external provider — so if step 5 blows up after the charge, we issue a
compensating refund and record the incident (see `_compensate_failed_order`).

Trade-off worth knowing: the charge (step 4) happens while the stock rows are
locked by our open transaction. With the in-process mock that is instant. With
a real gateway you would not hold row locks across a network call — you would
create the order as PENDING_PAYMENT, release the transaction, and confirm via
a webhook. That is the first thing to change at scale.
"""
import logging
from decimal import Decimal

from app.models.cart import CartItem
from app.models.order import Order, OrderItem, OrderStatus, OrderStatusHistory, SellerOrder
from app.models.payment import PaymentStatus
from app.models.seller_profile import SellerStatus
from app.repositories import (
    address_repository,
    cart_repository,
    inventory_repository,
    order_repository,
    payment_repository,
    product_repository,
    seller_repository,
)

logger = logging.getLogger("meraki.checkout")


class AddressNotFound(Exception):
    pass


class EmptyCart(Exception):
    pass


class ItemUnavailable(Exception):
    def __init__(self, product_name: str):
        super().__init__(product_name)
        self.product_name = product_name


class InsufficientStock(Exception):
    def __init__(self, product_name: str):
        super().__init__(product_name)
        self.product_name = product_name


class PaymentDeclined(Exception):
    def __init__(self, result):
        super().__init__(result.failure_reason)
        self.result = result


def _snapshot_address(address) -> dict:
    return {
        "full_name": address.full_name,
        "phone": address.phone,
        "address_line": address.address_line,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "country": address.country,
    }


def _build_lines(db, cart_items) -> list[dict]:
    """
    Re-validate every cart line against the database and price it. Returns
    plain dicts (no ORM objects) so they stay usable after a rollback.
    Lines are sorted by product id so concurrent checkouts always take stock
    in the same order — two carts holding the same products can't deadlock.
    """
    lines = []
    for item in sorted(cart_items, key=lambda i: str(i.product_id)):
        product = product_repository.get_by_id(db, item.product_id)
        if product is None or not product.is_active:
            raise ItemUnavailable(product.name if product else "An item in your cart")

        seller = seller_repository.get_by_id(db, product.seller_id)
        if seller is None or seller.status != SellerStatus.APPROVED:
            raise ItemUnavailable(product.name)

        if item.quantity > product.available_stock:
            raise InsufficientStock(product.name)

        unit_price = (
            product.discount_price if product.discount_price is not None else product.price
        )
        lines.append(
            {
                "product_id": product.id,
                "seller_id": product.seller_id,
                "product_name": product.name,
                "quantity": item.quantity,
                "list_price": product.price,
                "unit_price": unit_price,
            }
        )
    return lines


def _finalize_success(db, *, order_id, user_id, cart_id, total, result, payment_method):
    """Last step of the transaction: record the payment, empty the cart, commit."""
    payment_repository.add(
        db,
        order_id=order_id,
        user_id=user_id,
        amount=total,
        status=PaymentStatus.SUCCESS,
        provider=result.provider,
        payment_method=payment_method,
        transaction_reference=result.transaction_reference,
    )
    db.query(CartItem).filter(CartItem.cart_id == cart_id).delete(synchronize_session=False)
    db.commit()


def _record_failed_attempt(
    db, *, user_id, total, result, payment_method, status=None, reason=None
):
    """Persist a payment attempt that produced no order (own transaction)."""
    payment_repository.add(
        db,
        order_id=None,
        user_id=user_id,
        amount=total,
        status=status or result.status,
        provider=result.provider,
        payment_method=payment_method,
        transaction_reference=result.transaction_reference,
        failure_reason=reason or result.failure_reason,
    )
    db.commit()


def _compensate_failed_order(db, *, provider, result, user_id, total, payment_method):
    """
    The customer was charged but we could not save the order. Refund them and
    leave an audit row. Best effort: if the refund itself fails, shout — that
    case needs a human (reconciliation), and must never hide the original error.
    """
    try:
        provider.refund(result.transaction_reference)
        # CANCELLED, not SUCCESS: this row must never read as a live payment.
        _record_failed_attempt(
            db,
            user_id=user_id,
            total=total,
            result=result,
            payment_method=payment_method,
            status=PaymentStatus.CANCELLED,
            reason="Order could not be saved after a successful charge; charge refunded",
        )
    except Exception:
        db.rollback()
        logger.exception(
            "refund_failed_needs_reconciliation reference=%s user_id=%s",
            result.transaction_reference,
            user_id,
        )


def checkout(db, *, user, shipping_address_id, payment_method: str, provider) -> Order:
    user_id = user.id

    address = address_repository.get_for_user(db, user_id, shipping_address_id)
    if address is None:
        raise AddressNotFound()

    cart = cart_repository.get_or_create_cart(db, user_id)
    cart_id = cart.id
    cart_items = list(cart.items)
    if not cart_items:
        raise EmptyCart()

    lines = _build_lines(db, cart_items)

    subtotal = sum((l["list_price"] * l["quantity"] for l in lines), Decimal("0"))
    total = sum((l["unit_price"] * l["quantity"] for l in lines), Decimal("0"))
    discount_total = subtotal - total
    shipping_snapshot = _snapshot_address(address)

    charge_result = None
    try:
        # 2. Take stock. Any shortfall aborts everything (including units
        #    already taken from earlier lines — the rollback returns them).
        for line in lines:
            if inventory_repository.decrement_stock(db, line["product_id"], line["quantity"]) != 1:
                logger.warning(
                    "inventory_conflict product_id=%s requested=%s",
                    line["product_id"],
                    line["quantity"],
                )
                raise InsufficientStock(line["product_name"])

        # 3. Build the order.
        order = Order(
            user_id=user_id,
            subtotal=subtotal,
            discount_total=discount_total,
            total_amount=total,
            shipping_address=shipping_snapshot,
        )
        db.add(order)
        db.flush()
        order_id = order.id

        seller_orders: dict = {}
        for line in lines:
            seller_order = seller_orders.get(line["seller_id"])
            if seller_order is None:
                seller_order = SellerOrder(
                    order_id=order_id,
                    seller_id=line["seller_id"],
                    status=OrderStatus.PLACED,
                    total_amount=Decimal("0.00"),
                )
                db.add(seller_order)
                db.flush()
                seller_orders[line["seller_id"]] = seller_order

            seller_order.total_amount = seller_order.total_amount + (
                line["unit_price"] * line["quantity"]
            )
            db.add(
                OrderItem(
                    seller_order_id=seller_order.id,
                    product_id=line["product_id"],
                    product_name=line["product_name"],
                    quantity=line["quantity"],
                    list_price=line["list_price"],
                    unit_price=line["unit_price"],
                )
            )

        for seller_order in seller_orders.values():
            db.add(
                OrderStatusHistory(
                    seller_order_id=seller_order.id,
                    status=OrderStatus.PLACED,
                    changed_by_user_id=user_id,
                )
            )
        db.flush()

        # 4. Charge.
        charge_result = provider.charge(amount=total, payment_method=payment_method)
        if charge_result.status != PaymentStatus.SUCCESS:
            raise PaymentDeclined(charge_result)

        # 5. Persist payment, empty cart, commit.
        _finalize_success(
            db,
            order_id=order_id,
            user_id=user_id,
            cart_id=cart_id,
            total=total,
            result=charge_result,
            payment_method=payment_method,
        )

    except InsufficientStock:
        db.rollback()
        raise
    except PaymentDeclined as declined:
        db.rollback()
        _record_failed_attempt(
            db,
            user_id=user_id,
            total=total,
            result=declined.result,
            payment_method=payment_method,
        )
        logger.warning(
            "payment_failed user_id=%s status=%s reason=%s",
            user_id,
            declined.result.status.value,
            declined.result.failure_reason,
        )
        raise
    except Exception:
        db.rollback()
        if charge_result is not None and charge_result.status == PaymentStatus.SUCCESS:
            logger.error(
                "order_failed_after_charge reference=%s user_id=%s — refunding",
                charge_result.transaction_reference,
                user_id,
            )
            _compensate_failed_order(
                db,
                provider=provider,
                result=charge_result,
                user_id=user_id,
                total=total,
                payment_method=payment_method,
            )
        raise

    logger.info(
        "order_created order_id=%s user_id=%s total=%s lines=%d",
        order_id,
        user_id,
        total,
        len(lines),
    )
    return order_repository.get_for_user(db, user_id, order_id)
