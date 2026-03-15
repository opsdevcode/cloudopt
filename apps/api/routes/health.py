"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", status_code=200)
async def health():
    """Liveness/readiness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready():
    """Readiness (e.g. DB connectivity could be checked here)."""
    return {"status": "ready"}
