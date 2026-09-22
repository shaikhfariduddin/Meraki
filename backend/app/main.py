from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth

app = FastAPI(
    title="Marketplace API",
    description="Multi-vendor e-commerce marketplace backend.",
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


@app.get("/api/health", tags=["health"])
def health_check():
    """Simple liveness check — used by Render and by local smoke tests."""
    return {"status": "ok"}
