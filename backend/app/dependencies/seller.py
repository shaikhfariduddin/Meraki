from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.seller_profile import SellerStatus
from app.models.user import User, UserRole
from app.repositories import seller_repository


def get_current_approved_seller(
    current_user: User = Depends(require_role(UserRole.SELLER)),
    db: Session = Depends(get_db),
) -> User:
    """
    Stricter than require_role(SELLER): that only proves the user's
    *role* is seller. Suspension must take effect immediately — before
    their JWT expires — so this re-checks the live SellerProfile.status
    on every call rather than trusting the role claim alone. Used by
    product-management endpoints starting in the next stage.
    """
    profile = seller_repository.get_by_user_id(db, current_user.id)
    if profile is None or profile.status != SellerStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller account is not currently approved",
        )
    return current_user
