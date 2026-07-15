"""Shared pytest fixtures and collection hooks.

Testing lanes:
  * offline unit (default): sandbox LLM, no Postgres/Redis/keys/network
  * integration: Postgres-backed API tests (enqueue may be mocked)
  * e2e: live HTTP against Compose stack (see scripts/e2e-stack-smoke.sh)
"""

from __future__ import annotations

import os
from collections.abc import Iterator

# Force the offline sandbox LLM before any settings are loaded, so the unit lane needs no keys.
os.environ.setdefault("CLOUDOPT_LLM_MODE", "sandbox")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.api.main import app  # noqa: E402
from packages.core.config import get_settings  # noqa: E402


def _reset_database_module_cache() -> None:
    import packages.core.database as db_mod

    db_mod._engine = None
    db_mod._session_factory = None


@pytest.fixture(autouse=True)
def _reset_db_engine_cache() -> Iterator[None]:
    """Clear cached async engine between tests (avoids loop mismatch with pytest-asyncio)."""
    _reset_database_module_cache()
    yield
    _reset_database_module_cache()


def _database_reachable() -> bool:
    """Best-effort check that the sync Postgres URL is reachable (short timeout)."""
    try:
        from sqlalchemy import create_engine, text

        url = get_settings().database_url_sync
        engine = create_engine(url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:  # noqa: BLE001 — any failure means "not reachable", skip integration
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip integration-marked tests when the database is unreachable."""
    if _database_reachable():
        return
    skip = pytest.mark.skip(reason="integration: database unreachable (offline unit lane)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
async def async_session() -> AsyncSession:
    """Async DB session for integration tests (uses configured database URL)."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def api_client() -> AsyncClient:
    """In-process HTTP client against the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
