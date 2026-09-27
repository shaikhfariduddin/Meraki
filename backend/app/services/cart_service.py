"""
Cart business logic.

Every mutation re-validates the product against the database — active
status and available stock — rather than trusting anything the client
last saw. Price is always read fresh from the product too; a cart is
not a commitment, so unlike OrderItem later, nothing here freezes a
price at add-to-cart time.
"""
from decimal import Decimal

from app.repositories import cart_repository, product_repository


class ProductNotFound(Exception):
    pass


class ProductInactive(Exception):
    pass


class InsufficientStock(Exception):
    pass


class ItemNotFound(Exception):
    pass


def _validate_product_for_purchase(product, requested_quantity: int):
    if product is None:
        raise ProductNotFound()
    if not product.is_active:
        raise ProductInactive()
    if requested_quantity > product.available_stock:
        raise InsufficientStock()


def add_to_cart(db, *, user, product_id, quantity: int):
    product = product_repository.get_by_id(db, product_id)
    cart = cart_repository.get_or_create_cart(db, user.id)
    existing = cart_repository.get_item_by_product(db, cart.id, product_id)
    combined_quantity = quantity + (existing.quantity if existing else 0)

    _validate_product_for_purchase(product, combined_quantity)

    if existing:
        existing.quantity = combined_quantity
        return cart_repository.save_item(db, existing)
    return cart_repository.add_item(
        db, cart_id=cart.id, product_id=product_id, quantity=quantity
    )


def update_quantity(db, *, user, item_id, quantity: int):
    cart = cart_repository.get_or_create_cart(db, user.id)
    item = cart_repository.get_item(db, cart.id, item_id)
    if item is None:
        raise ItemNotFound()

    product = product_repository.get_by_id(db, item.product_id)
    _validate_product_for_purchase(product, quantity)

    item.quantity = quantity
    return cart_repository.save_item(db, item)


def remove_item(db, *, user, item_id):
    cart = cart_repository.get_or_create_cart(db, user.id)
    item = cart_repository.get_item(db, cart.id, item_id)
    if item is None:
        raise ItemNotFound()
    cart_repository.delete_item(db, item)


def clear_cart(db, *, user):
    cart = cart_repository.get_or_create_cart(db, user.id)
    cart_repository.clear(db, cart)


def view_cart(db, *, user):
    cart = cart_repository.get_or_create_cart(db, user.id)

    items_out = []
    subtotal = Decimal("0")
    item_count = 0

    for item in cart.items:
        product = product_repository.get_by_id(db, item.product_id)

        if product is None:
            # Product was hard-deleted (shouldn't normally happen — products
            # are deactivated, not deleted) — show a placeholder rather than
            # crash, and exclude it from the subtotal.
            items_out.append(
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": "Unavailable product",
                    "unit_price": Decimal("0"),
                    "quantity": item.quantity,
                    "line_total": Decimal("0"),
                    "product_is_active": False,
                    "available_stock": 0,
                }
            )
            continue

        unit_price = product.discount_price if product.discount_price is not None else product.price
        line_total = unit_price * item.quantity
        items_out.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": product.name,
                "unit_price": unit_price,
                "quantity": item.quantity,
                "line_total": line_total,
                "product_is_active": product.is_active,
                "available_stock": product.available_stock,
            }
        )

        # A deactivated product stays visible in the cart (so the customer
        # can see and remove it) but doesn't count toward the total they'd
        # actually be charged.
        if product.is_active:
            subtotal += line_total
            item_count += item.quantity

    return {"items": items_out, "subtotal": subtotal, "item_count": item_count}
