"""
/api/sellers/* - a customer applying for seller access, checking the
status of their own application, and (once approved) their analytics.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.seller import get_current_seller_profile
from app.models.seller_profile import SellerProfile
from app.models.user import User
from app.repositories import analytics_repository, seller_repository
from app.schemas.analytics import SellerAnalyticsOut
from app.schemas.seller import SellerApplicationCreate, SellerProfileOut
from app.services import seller_service

router = APIRouter(prefix="/api/sellers", tags=["sellers"])


@router.post("/apply", response_model=SellerProfileOut, status_code=status.HTTP_201_CREATED)
def apply(
    payload: SellerApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return seller_service.apply_for_seller(
            db, user=current_user, business_name=payload.business_name
        )
    except seller_service.AlreadyApplied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending or approved seller application",
        )
    except seller_service.InvalidTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/me", response_model=SellerProfileOut)
def my_application(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = seller_repository.get_by_user_id(db, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No seller application found"
        )
    return profile


@router.get("/analytics", response_model=SellerAnalyticsOut)
def my_analytics(
    seller_profile: SellerProfile = Depends(get_current_seller_profile),
    db: Session = Depends(get_db),
):
    return analytics_repository.seller_summary(db, seller_profile.id)
