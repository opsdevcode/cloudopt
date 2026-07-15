"""Shared pytest fixtures and collection hooks.

Two testing lanes:
  * offline unit (default): sandbox LLM, no Postgres/Redis/keys/network. A bare clone runs green.
  * integration (``@pytest.mark.integration``): needs Postgres; auto-skipped when unreachable.
"""

from __future__ import annotations

import os

# Force the offline sandbox LLM before any settings are loaded, so the unit lane needs no keys.
os.environ.setdefault("CLOUDOPT_LLM_MODE", "sandbox")

import pytest  # noqa: E402


def _database_reachable() -> bool:
    """Best-effort check that the sync Postgres URL is reachable (short timeout)."""
    try:
        from sqlalchemy import create_engine, text

        from packages.core.config import get_settings

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
