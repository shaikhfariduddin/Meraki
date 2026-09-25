"""
/api/admin/* — every route here requires ADMIN, enforced once at the
router level rather than repeated on each endpoint.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.seller_profile import SellerStatus
from app.models.user import UserRole
from app.repositories import seller_repository
from app.schemas.seller import SellerProfileOut, SellerReviewRequest
from app.services import seller_service

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.get("/sellers", response_model=list[SellerProfileOut])
def list_sellers(
    status_filter: SellerStatus | None = Query(default=SellerStatus.PENDING, alias="status"),
    db: Session = Depends(get_db),
):
    return seller_repository.list_by_status(db, status_filter)


@router.post("/sellers/{seller_id}/approve", response_model=SellerProfileOut)
def approve_seller(seller_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return seller_service.approve(db, seller_id=seller_id)
    except seller_service.ApplicationNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    except seller_service.InvalidTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/sellers/{seller_id}/reject", response_model=SellerProfileOut)
def reject_seller(
    seller_id: uuid.UUID,
    payload: SellerReviewRequest | None = None,
    db: Session = Depends(get_db),
):
    reason = payload.reason if payload else None
    try:
        return seller_service.reject(db, seller_id=seller_id, reason=reason)
    except seller_service.ApplicationNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    except seller_service.InvalidTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/sellers/{seller_id}/suspend", response_model=SellerProfileOut)
def suspend_seller(
    seller_id: uuid.UUID,
    payload: SellerReviewRequest | None = None,
    db: Session = Depends(get_db),
):
    reason = payload.reason if payload else None
    try:
        return seller_service.suspend(db, seller_id=seller_id, reason=reason)
    except seller_service.ApplicationNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    except seller_service.InvalidTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
