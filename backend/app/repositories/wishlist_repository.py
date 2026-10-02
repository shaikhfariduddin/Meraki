import uuid

from sqlalchemy.orm import Session

from app.models.wishlist import Wishlist, WishlistItem


def get_or_create(db: Session, user_id: uuid.UUID) -> Wishlist:
    wishlist = db.query(Wishlist).filter(Wishlist.user_id == user_id).first()
    if wishlist is None:
        wishlist = Wishlist(user_id=user_id)
        db.add(wishlist)
        db.commit()
        db.refresh(wishlist)
    return wishlist


def get_item_by_product(
    db: Session, wishlist_id: uuid.UUID, product_id: uuid.UUID
) -> WishlistItem | None:
    return (
        db.query(WishlistItem)
        .filter(WishlistItem.wishlist_id == wishlist_id, WishlistItem.product_id == product_id)
        .first()
    )


def get_item(db: Session, wishlist_id: uuid.UUID, item_id: uuid.UUID) -> WishlistItem | None:
    return (
        db.query(WishlistItem)
        .filter(WishlistItem.id == item_id, WishlistItem.wishlist_id == wishlist_id)
        .first()
    )


def add_item(db: Session, *, wishlist_id: uuid.UUID, product_id: uuid.UUID) -> WishlistItem:
    item = WishlistItem(wishlist_id=wishlist_id, product_id=product_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: WishlistItem) -> None:
    db.delete(item)
    db.commit()
