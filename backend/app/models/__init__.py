# Importing every model module here means anything that imports `app.models`
# (Alembic's env.py, the test suite) gets the complete table registry — and
# string-based relationship() targets like "Payment" always resolve.
from app.models import (  # noqa: F401
    address,
    cart,
    category,
    order,
    payment,
    product,
    seller_profile,
    user,
)
