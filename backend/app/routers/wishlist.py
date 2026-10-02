import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.wishlist import WishlistItemAdd, WishlistOut
from app.services import wishlist_service

router = APIRouter(prefix="/api/wishlist", tags=["wishlist"])


@router.get("", response_model=WishlistOut)
def view_wishlist(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return wishlist_service.view_wishlist(db, user=current_user)


@router.post("/items", response_model=WishlistOut, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: WishlistItemAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        wishlist_service.add_to_wishlist(db, user=current_user, product_id=payload.product_id)
    except wishlist_service.ProductNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    except wishlist_service.AlreadyInWishlist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Product already in wishlist"
        )
    return wishlist_service.view_wishlist(db, user=current_user)


@router.delete("/items/{item_id}", response_model=WishlistOut)
def remove_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        wishlist_service.remove_item(db, user=current_user, item_id=item_id)
    except wishlist_service.ItemNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found"
        )
    return wishlist_service.view_wishlist(db, user=current_user)
