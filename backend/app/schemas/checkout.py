import uuid
from enum import Enum

from pydantic import BaseModel


class PaymentMethod(str, Enum):
    """Mock methods only — they let a demo (or a test) pick the outcome."""

    MOCK_SUCCESS = "mock_success"
    MOCK_FAIL = "mock_fail"
    MOCK_CANCEL = "mock_cancel"


class CheckoutRequest(BaseModel):
    # Deliberately tiny. The cart lives on the server, and prices, discounts,
    # stock and totals are all recomputed there — nothing money-related is
    # accepted from the client.
    shipping_address_id: uuid.UUID
    payment_method: PaymentMethod = PaymentMethod.MOCK_SUCCESS
