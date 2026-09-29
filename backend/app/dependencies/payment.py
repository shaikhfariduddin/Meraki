from app.services.payment_provider import MockPaymentProvider, PaymentProvider

_provider = MockPaymentProvider()


def get_payment_provider() -> PaymentProvider:
    """Single place that decides which provider the app uses. Tests override
    this dependency; a real deployment would return a real provider here."""
    return _provider
