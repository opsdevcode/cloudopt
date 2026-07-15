"""Health check endpoints."""

from fastapi import APIRouter, Response
from sqlalchemy import text

from packages.core.database import get_async_engine

router = APIRouter()


@router.get("/health", status_code=200)
async def health():
    """Liveness probe (no dependencies)."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(response: Response):
    """Readiness probe: verifies the database is reachable and migrated."""
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            # `scans` exists only after migrations run; use it to detect an unmigrated DB.
            await conn.execute(text("SELECT 1 FROM scans LIMIT 1"))
    except Exception as exc:  # noqa: BLE001 — readiness must report, not raise
        response.status_code = 503
        return {"status": "not ready", "detail": str(exc)[:200]}
    return {"status": "ready"}
