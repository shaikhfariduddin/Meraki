import uuid

from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem


def get_or_create_cart(db: Session, user_id: uuid.UUID) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def get_item(db: Session, cart_id: uuid.UUID, item_id: uuid.UUID) -> CartItem | None:
    return (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart_id)
        .first()
    )


def get_item_by_product(
    db: Session, cart_id: uuid.UUID, product_id: uuid.UUID
) -> CartItem | None:
    return (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        .first()
    )


def add_item(db: Session, *, cart_id: uuid.UUID, product_id: uuid.UUID, quantity: int) -> CartItem:
    item = CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def save_item(db: Session, item: CartItem) -> CartItem:
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: CartItem) -> None:
    db.delete(item)
    db.commit()


def clear(db: Session, cart: Cart) -> None:
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
