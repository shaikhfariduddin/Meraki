"""
/api/sellers/orders — a seller managing orders containing their own
products.

Deliberately uses require_role(SELLER), not get_current_approved_seller:
a seller SUSPENDED from listing new products must still be able to see
and responsibly wind down (cancel) orders already placed against them —
approval gates *new* listings, not existing obligations.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.repositories import seller_repository
from app.schemas.order import SellerOrderDetailOut, SellerOrderListOut, SellerOrderStatusUpdate
from app.services import seller_order_service

router = APIRouter(prefix="/api/sellers/orders", tags=["seller-orders"])


def _seller_profile_or_404(db: Session, user: User):
    profile = seller_repository.get_by_user_id(db, user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No seller profile found"
        )
    return profile


@router.get("", response_model=SellerOrderListOut)
def list_seller_orders(
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role(UserRole.SELLER)),
    db: Session = Depends(get_db),
):
    seller_profile = _seller_profile_or_404(db, current_user)
    items, total = seller_order_service.list_for_seller(
        db, seller_profile=seller_profile, status=status_filter, page=page, page_size=page_size
    )
    return SellerOrderListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{seller_order_id}", response_model=SellerOrderDetailOut)
def get_seller_order(
    seller_order_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.SELLER)),
    db: Session = Depends(get_db),
):
    seller_profile = _seller_profile_or_404(db, current_user)
    try:
        return seller_order_service.get_for_seller(
            db, seller_profile=seller_profile, seller_order_id=seller_order_id
        )
    except seller_order_service.SellerOrderNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


@router.patch("/{seller_order_id}/status", response_model=SellerOrderDetailOut)
def update_seller_order_status(
    seller_order_id: uuid.UUID,
    payload: SellerOrderStatusUpdate,
    current_user: User = Depends(require_role(UserRole.SELLER)),
    db: Session = Depends(get_db),
):
    seller_profile = _seller_profile_or_404(db, current_user)
    try:
        return seller_order_service.update_status(
            db,
            seller_profile=seller_profile,
            seller_order_id=seller_order_id,
            new_status=payload.status,
            changed_by_user_id=current_user.id,
        )
    except seller_order_service.SellerOrderNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    except seller_order_service.InvalidStatusTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
