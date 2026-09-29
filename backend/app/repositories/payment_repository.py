from app.models.payment import Payment


def add(db, **fields) -> Payment:
    """Stage a payment row. Deliberately does not commit — the checkout
    service decides whether it belongs to the order's transaction or stands
    alone (a failed attempt)."""
    payment = Payment(**fields)
    db.add(payment)
    db.flush()
    return payment
