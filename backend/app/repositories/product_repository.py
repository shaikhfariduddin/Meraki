import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.product import Inventory, Product, ProductImage


def get_by_id(db: Session, product_id: uuid.UUID) -> Product | None:
    return (
        db.query(Product)
        .options(joinedload(Product.images), joinedload(Product.inventory))
        .filter(Product.id == product_id)
        .first()
    )


def list_by_seller(db: Session, seller_id: uuid.UUID) -> list[Product]:
    return (
        db.query(Product)
        .options(joinedload(Product.images), joinedload(Product.inventory))
        .filter(Product.seller_id == seller_id)
        .order_by(Product.created_at.desc())
        .all()
    )


def search_active(
    db: Session,
    *,
    keyword: str | None = None,
    category_id: uuid.UUID | None = None,
    seller_id: uuid.UUID | None = None,
    brand: str | None = None,
    min_price=None,
    max_price=None,
    in_stock_only: bool = False,
    sort: str = "newest",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Product], int]:
    query = (
        db.query(Product)
        .options(joinedload(Product.images), joinedload(Product.inventory))
        .filter(Product.is_active.is_(True))
    )

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)
    if brand is not None:
        query = query.filter(Product.brand.ilike(brand))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(Product.name.ilike(like), Product.description.ilike(like))
        )
    if in_stock_only:
        # .has() -> correlated EXISTS subquery. A plain .join(Inventory)
        # here would collide with the joinedload above (which builds its
        # own aliased join for eager-loading) and risk duplicate rows.
        query = query.filter(Product.inventory.has(Inventory.available_stock > 0))

    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def create(
    db: Session,
    *,
    seller_id,
    category_id,
    name,
    description,
    price,
    discount_price,
    brand,
    attributes,
    initial_stock,
    image_urls,
) -> Product:
    product = Product(
        seller_id=seller_id,
        category_id=category_id,
        name=name,
        description=description,
        price=price,
        discount_price=discount_price,
        brand=brand,
        attributes=attributes,
    )
    db.add(product)
    db.flush()  # assigns product.id before we create children that reference it

    db.add(Inventory(product_id=product.id, available_stock=initial_stock))
    for i, url in enumerate(image_urls):
        db.add(ProductImage(product_id=product.id, url=url, sort_order=i))

    db.commit()
    db.refresh(product)
    return product


def save(db: Session, product: Product) -> Product:
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_stock(db: Session, product: Product, new_available_stock: int) -> Product:
    product.inventory.available_stock = new_available_stock
    db.add(product.inventory)
    db.commit()
    db.refresh(product)
    return product
