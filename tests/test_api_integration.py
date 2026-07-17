"""Integration tests for API endpoints (Postgres required)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ready_after_migrate(api_client: AsyncClient) -> None:
    """Readiness probe succeeds when migrations have created the scans table."""
    response = await api_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_list_scan(api_client: AsyncClient) -> None:
    """Create a scan and verify it appears in the list."""
    with patch("apps.api.routes.scans.enqueue_dispatch_scan"):
        create = await api_client.post(
            "/api/v1/scans",
            json={"scan_kind": "finops", "tenant_id": "test-tenant"},
        )
    assert create.status_code == 200
    body = create.json()
    assert body["scan_kind"] == "finops"
    assert body["tenant_id"] == "test-tenant"
    assert body["status"] == "pending"
    scan_id = body["id"]

    listing = await api_client.get("/api/v1/scans")
    assert listing.status_code == 200
    ids = [s["id"] for s in listing.json()]
    assert scan_id in ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_findings_empty(api_client: AsyncClient) -> None:
    """Findings list returns 200 with a list body."""
    response = await api_client.get("/api/v1/findings")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_overview(api_client: AsyncClient) -> None:
    """Overview metrics returns expected aggregate keys."""
    response = await api_client.get("/api/v1/metrics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "findings_total" in data
    assert "scans_total" in data
    assert "findings_by_severity" in data
    assert "recent_scans" in data
    assert isinstance(data["recent_scans"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_search_empty(api_client: AsyncClient) -> None:
    """RAG search returns a list (possibly empty) for unknown tenant."""
    response = await api_client.get(
        "/api/v1/rag/search",
        params={"tenant_id": "no-chunks-tenant", "q": "cost optimization"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_search_after_ingest(api_client: AsyncClient, async_session) -> None:
    """Seeded chunk is searchable via API."""
    from packages.ai.llm_client import AsyncSandboxLLMClient
    from packages.ai.rag import ingest_chunk_async

    client = AsyncSandboxLLMClient(embedding_dimensions=1024)
    await ingest_chunk_async(
        async_session,
        "rag-api-tenant",
        "finding",
        "seed-f1",
        "Rightsize EKS node groups for cost savings",
        client=client,
    )
    await async_session.commit()

    response = await api_client.get(
        "/api/v1/rag/search",
        params={"tenant_id": "rag-api-tenant", "q": "EKS cost", "limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["source_type"] == "finding"
    assert "EKS" in body[0]["content"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_ask_sandbox(api_client: AsyncClient) -> None:
    """Ask endpoint works in sandbox mode without live LLM."""
    response = await api_client.post(
        "/api/v1/rag/ask",
        json={"tenant_id": "default", "question": "What cost risks do we have?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sandbox"] is True
    assert "question" in data["answer"].lower() or "Sandbox" in data["answer"]
    assert isinstance(data["chunks_used"], list)
