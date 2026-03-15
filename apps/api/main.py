"""CloudOpt API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.routes import health, scans, findings
from packages.core.database import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    yield
    # Cleanup if needed


app = FastAPI(
    title="CloudOpt API",
    description="AI-powered FinOps platform for AWS and Kubernetes cost optimization",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["health"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(findings.router, prefix="/api/v1/findings", tags=["findings"])


@app.get("/")
async def root():
    """Root redirect or info."""
    return {"service": "cloudopt", "docs": "/docs"}
