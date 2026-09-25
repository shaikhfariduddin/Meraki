"""
Product business logic: creation, updates, deactivation, stock changes.

Ownership is enforced here, not just at the route level — every
mutating function takes the seller_profile making the request and
checks it against product.seller_id before doing anything.
"""
from app.repositories import category_repository, product_repository


class CategoryNotFound(Exception):
    pass


class ProductNotFound(Exception):
    pass


class NotProductOwner(Exception):
    pass


def create_product(db, *, seller_profile, payload):
    if category_repository.get_by_id(db, payload.category_id) is None:
        raise CategoryNotFound(payload.category_id)

    return product_repository.create(
        db,
        seller_id=seller_profile.id,
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        discount_price=payload.discount_price,
        brand=payload.brand,
        attributes=payload.attributes,
        initial_stock=payload.initial_stock,
        image_urls=payload.image_urls,
    )


def _get_owned_product(db, *, seller_profile, product_id):
    product = product_repository.get_by_id(db, product_id)
    if product is None:
        raise ProductNotFound(product_id)
    if product.seller_id != seller_profile.id:
        raise NotProductOwner(product_id)
    return product


def update_product(db, *, seller_profile, product_id, payload):
    product = _get_owned_product(db, seller_profile=seller_profile, product_id=product_id)

    # exclude_unset (not just "is not None") so a field can be explicitly
    # cleared to null (e.g. removing a discount) vs. simply not sent.
    updates = payload.model_dump(exclude_unset=True)

    if "category_id" in updates:
        if category_repository.get_by_id(db, updates["category_id"]) is None:
            raise CategoryNotFound(updates["category_id"])
        product.category_id = updates["category_id"]

    for field in ("name", "description", "price", "discount_price", "brand", "attributes"):
        if field in updates:
            setattr(product, field, updates[field])

    return product_repository.save(db, product)


def deactivate_product(db, *, seller_profile, product_id):
    product = _get_owned_product(db, seller_profile=seller_profile, product_id=product_id)
    product.is_active = False
    return product_repository.save(db, product)


def update_stock(db, *, seller_profile, product_id, available_stock):
    product = _get_owned_product(db, seller_profile=seller_profile, product_id=product_id)
    return product_repository.update_stock(db, product, available_stock)
