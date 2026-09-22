from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="Marketplace API",
    description="Multi-vendor e-commerce marketplace backend.",
    version="0.1.0",
)


@app.get("/api/health", tags=["health"])
def health_check():
    """Simple liveness check — used by Render and by local smoke tests."""
    return {"status": "ok"}
