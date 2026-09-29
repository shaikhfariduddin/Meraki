"""
/api/checkout — the client says WHERE to ship and HOW to pay; everything
else (items, prices, discounts, stock, totals) is read and computed on the
server. Failure modes map to distinct status codes so a client can react.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.payment import get_payment_provider
from app.models.user import User
from app.schemas.checkout import CheckoutRequest
from app.schemas.order import OrderOut
from app.services import checkout_service
from app.services.payment_provider import PaymentProvider

router = APIRouter(prefix="/api/checkout", tags=["checkout"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Cart is empty"},
        402: {"description": "Payment failed or was cancelled — nothing was ordered"},
        404: {"description": "Shipping address not found (or not yours)"},
        409: {"description": "An item is unavailable or out of stock"},
    },
)
def place_order(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    provider: PaymentProvider = Depends(get_payment_provider),
):
    try:
        return checkout_service.checkout(
            db,
            user=current_user,
            shipping_address_id=payload.shipping_address_id,
            payment_method=payload.payment_method.value,
            provider=provider,
        )
    except checkout_service.AddressNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    except checkout_service.EmptyCart:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your cart is empty")
    except checkout_service.ItemUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{exc.product_name}' is no longer available",
        )
    except checkout_service.InsufficientStock as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Not enough stock for '{exc.product_name}'",
        )
    except checkout_service.PaymentDeclined as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment {exc.result.status.value}: {exc.result.failure_reason}",
        )
