import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.order import OrderStatus, SellerOrder


def _with_children(query):
    return query.options(
        selectinload(SellerOrder.items),
        selectinload(SellerOrder.history),
        selectinload(SellerOrder.order),
    )


def get_for_seller(
    db: Session, seller_id: uuid.UUID, seller_order_id: uuid.UUID
) -> SellerOrder | None:
    return (
        _with_children(db.query(SellerOrder))
        .filter(SellerOrder.id == seller_order_id, SellerOrder.seller_id == seller_id)
        .first()
    )


def list_for_seller(
    db: Session,
    seller_id: uuid.UUID,
    *,
    status: OrderStatus | None,
    page: int,
    page_size: int,
) -> tuple[list[SellerOrder], int]:
    base = db.query(SellerOrder).filter(SellerOrder.seller_id == seller_id)
    if status is not None:
        base = base.filter(SellerOrder.status == status)
    total = base.count()
    items = (
        _with_children(base)
        .order_by(SellerOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total
