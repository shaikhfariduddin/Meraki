from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    addresses,
    admin,
    auth,
    cart,
    categories,
    checkout,
    orders,
    products,
    seller_orders,
    sellers,
)

app = FastAPI(
    title="Meraki API",
    description="Meraki — multi-vendor e-commerce marketplace backend.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sellers.router)
app.include_router(admin.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(addresses.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(seller_orders.router)


@app.get("/api/health", tags=["health"])
def health_check():
    """Simple liveness check — used by Render and by local smoke tests."""
    return {"status": "ok"}
