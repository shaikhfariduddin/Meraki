import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, SellerOrder


def _with_children(query):
    # selectinload (one extra query per level) rather than joinedload: joining
    # several collections at once multiplies rows.
    return query.options(
        selectinload(Order.seller_orders).options(
            selectinload(SellerOrder.items),
            selectinload(SellerOrder.history),
        ),
        selectinload(Order.payment),
    )


def get_for_user(db: Session, user_id: uuid.UUID, order_id: uuid.UUID) -> Order | None:
    return (
        _with_children(db.query(Order))
        .filter(Order.id == order_id, Order.user_id == user_id)
        .first()
    )


def list_for_user(
    db: Session, user_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[Order], int]:
    base = db.query(Order).filter(Order.user_id == user_id)
    total = base.count()
    orders = (
        _with_children(base)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return orders, total
