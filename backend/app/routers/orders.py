"""/api/orders — a customer's own order history. Owner-only, 404 otherwise."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.order import OrderListOut, OrderOut
from app.services import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=OrderListOut)
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders, total = order_service.list_orders(
        db, user=current_user, page=page, page_size=page_size
    )
    return OrderListOut(items=orders, total=total, page=page, page_size=page_size)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return order_service.get_order(db, user=current_user, order_id=order_id)
    except order_service.OrderNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
