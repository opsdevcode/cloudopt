"""Helpers for polling scan state in integration/e2e tests."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from httpx import AsyncClient, Client


async def wait_for_scan_async(
    client: AsyncClient,
    scan_id: str,
    *,
    timeout: float = 60.0,
    poll_interval: float = 0.5,
) -> dict[str, Any]:
    """Poll until scan reaches a terminal status (completed or failed)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = await client.get(f"/api/v1/scans/{scan_id}")
        response.raise_for_status()
        body = response.json()
        status = body.get("status")
        if status in ("completed", "failed"):
            return body
        await asyncio.sleep(poll_interval)
    msg = f"Scan {scan_id} did not finish within {timeout}s"
    raise TimeoutError(msg)


def wait_for_scan_sync(
    client: Client,
    base_url: str,
    scan_id: str,
    *,
    timeout: float = 60.0,
    poll_interval: float = 0.5,
) -> dict[str, Any]:
    """Sync poll for CLI tests against a live HTTP API."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"{base_url}/api/v1/scans/{scan_id}")
        response.raise_for_status()
        body = response.json()
        status = body.get("status")
        if status in ("completed", "failed"):
            return body
        time.sleep(poll_interval)
    msg = f"Scan {scan_id} did not finish within {timeout}s"
    raise TimeoutError(msg)
