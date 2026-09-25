import uuid

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


def list_active(db: Session, *, skip: int = 0, limit: int = 20) -> list[Product]:
    return (
        db.query(Product)
        .options(joinedload(Product.images), joinedload(Product.inventory))
        .filter(Product.is_active.is_(True))
        .order_by(Product.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


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
