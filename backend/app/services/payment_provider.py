"""
Payment provider abstraction.

Checkout depends on `PaymentProvider`, never on a concrete gateway. Swapping
in a real provider later means writing one new subclass — checkout is not
touched. `MockPaymentProvider` is a demo/test double and is NOT a payment
gateway: it moves no money and stores nothing sensitive.
"""
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.models.payment import PaymentStatus


@dataclass(frozen=True)
class PaymentResult:
    status: PaymentStatus
    transaction_reference: str
    provider: str
    failure_reason: str | None = None


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def charge(self, *, amount: Decimal, payment_method: str) -> PaymentResult:
        """Attempt to collect `amount`."""

    @abstractmethod
    def refund(self, transaction_reference: str) -> bool:
        """Reverse a previous successful charge. True if the refund went through."""


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def charge(self, *, amount: Decimal, payment_method: str) -> PaymentResult:
        reference = f"mock_{uuid.uuid4().hex}"
        if payment_method == "mock_fail":
            return PaymentResult(
                PaymentStatus.FAILED, reference, self.name, "Card declined (simulated)"
            )
        if payment_method == "mock_cancel":
            return PaymentResult(
                PaymentStatus.CANCELLED, reference, self.name, "Payment cancelled (simulated)"
            )
        return PaymentResult(PaymentStatus.SUCCESS, reference, self.name)

    def refund(self, transaction_reference: str) -> bool:
        return True
