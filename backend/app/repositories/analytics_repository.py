import uuid
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus, SellerOrder
from app.models.payment import Payment, PaymentStatus
from app.models.product import Inventory, Product
from app.models.seller_profile import SellerProfile, SellerStatus
from app.models.user import User

LOW_STOCK_THRESHOLD = 5


def _to_decimal(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def admin_summary(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_sellers = (
        db.query(func.count(SellerProfile.id))
        .filter(SellerProfile.status == SellerStatus.APPROVED)
        .scalar()
        or 0
    )
    total_products = (
        db.query(func.count(Product.id)).filter(Product.is_active.is_(True)).scalar() or 0
    )
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_revenue = _to_decimal(
        db.query(func.sum(Payment.amount)).filter(Payment.status == PaymentStatus.SUCCESS).scalar()
    )
    pending_orders = (
        db.query(func.count(func.distinct(SellerOrder.order_id)))
        .filter(SellerOrder.status.notin_([OrderStatus.DELIVERED, OrderStatus.CANCELLED]))
        .scalar()
        or 0
    )
    low_stock_products = (
        db.query(func.count(Inventory.id))
        .filter(Inventory.available_stock < LOW_STOCK_THRESHOLD)
        .scalar()
        or 0
    )
    return {
        "total_users": total_users,
        "total_sellers": total_sellers,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "low_stock_products": low_stock_products,
    }


def seller_summary(db: Session, seller_id: uuid.UUID) -> dict:
    total_products = (
        db.query(func.count(Product.id)).filter(Product.seller_id == seller_id).scalar() or 0
    )
    active_products = (
        db.query(func.count(Product.id))
        .filter(Product.seller_id == seller_id, Product.is_active.is_(True))
        .scalar()
        or 0
    )
    total_orders = (
        db.query(func.count(SellerOrder.id)).filter(SellerOrder.seller_id == seller_id).scalar()
        or 0
    )
    total_revenue = _to_decimal(
        db.query(func.sum(SellerOrder.total_amount))
        .filter(SellerOrder.seller_id == seller_id, SellerOrder.status != OrderStatus.CANCELLED)
        .scalar()
    )
    low_stock_products = (
        db.query(func.count(Inventory.id))
        .join(Product, Product.id == Inventory.product_id)
        .filter(Product.seller_id == seller_id, Inventory.available_stock < LOW_STOCK_THRESHOLD)
        .scalar()
        or 0
    )
    return {
        "total_products": total_products,
        "active_products": active_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "low_stock_products": low_stock_products,
    }
