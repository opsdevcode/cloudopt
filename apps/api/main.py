"""CloudOpt API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import findings, health, metrics, scans
from packages.core.config import get_settings


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

# Browser UI: set CLOUDOPT_CORS_ORIGINS (comma-separated) for cross-origin access.
_cors = get_settings().cors_origins.strip()
if _cors:
    _origins = [o.strip() for o in _cors.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router, tags=["health"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(findings.router, prefix="/api/v1/findings", tags=["findings"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])


@app.get("/")
async def root():
    """Root redirect or info."""
    return {"service": "cloudopt", "docs": "/docs"}
