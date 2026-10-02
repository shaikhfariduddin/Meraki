from decimal import Decimal

from app.repositories import product_repository, wishlist_repository


class ProductNotFound(Exception):
    pass


class AlreadyInWishlist(Exception):
    pass


class ItemNotFound(Exception):
    pass


def add_to_wishlist(db, *, user, product_id):
    product = product_repository.get_by_id(db, product_id)
    if product is None:
        raise ProductNotFound()

    wishlist = wishlist_repository.get_or_create(db, user.id)
    if wishlist_repository.get_item_by_product(db, wishlist.id, product_id) is not None:
        raise AlreadyInWishlist()

    return wishlist_repository.add_item(db, wishlist_id=wishlist.id, product_id=product_id)


def remove_item(db, *, user, item_id):
    wishlist = wishlist_repository.get_or_create(db, user.id)
    item = wishlist_repository.get_item(db, wishlist.id, item_id)
    if item is None:
        raise ItemNotFound()
    wishlist_repository.delete_item(db, item)


def view_wishlist(db, *, user):
    wishlist = wishlist_repository.get_or_create(db, user.id)
    items_out = []
    for item in wishlist.items:
        product = product_repository.get_by_id(db, item.product_id)
        items_out.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": product.name if product else "Unavailable product",
                "price": product.price if product else Decimal("0"),
                "product_is_active": product.is_active if product else False,
                "available_stock": product.available_stock if product else 0,
            }
        )
    return {"items": items_out}
