"""
/api/cart — a customer's persistent, database-backed cart. Every
mutating endpoint re-validates the product server-side and returns
the freshly recomputed cart, so the client is never asked to compute
or carry forward a subtotal itself.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartItemQuantityUpdate, CartOut
from app.services import cart_service

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _run(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except cart_service.ProductNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    except cart_service.ProductInactive:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Product is no longer available"
        )
    except cart_service.InsufficientStock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Not enough stock available"
        )
    except cart_service.ItemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")


@router.get("", response_model=CartOut)
def view_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return cart_service.view_cart(db, user=current_user)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _run(
        cart_service.add_to_cart,
        db,
        user=current_user,
        product_id=payload.product_id,
        quantity=payload.quantity,
    )
    return cart_service.view_cart(db, user=current_user)


@router.patch("/items/{item_id}", response_model=CartOut)
def update_item(
    item_id: uuid.UUID,
    payload: CartItemQuantityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _run(
        cart_service.update_quantity,
        db,
        user=current_user,
        item_id=item_id,
        quantity=payload.quantity,
    )
    return cart_service.view_cart(db, user=current_user)


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _run(cart_service.remove_item, db, user=current_user, item_id=item_id)
    return cart_service.view_cart(db, user=current_user)


@router.delete("", response_model=CartOut)
def clear_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cart_service.clear_cart(db, user=current_user)
    return cart_service.view_cart(db, user=current_user)
