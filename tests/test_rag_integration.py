"""RAG integration tests (Postgres + pgvector required)."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from packages.ai.llm_client import AsyncSandboxLLMClient
from packages.ai.rag import (
    ingest_chunk_async,
    retrieve_hits_async,
)
from packages.core.models import RagChunk


@pytest.fixture
def sandbox_embed_client() -> AsyncSandboxLLMClient:
    return AsyncSandboxLLMClient(embedding_dimensions=1024)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_upsert_replaces_duplicate(async_session, sandbox_embed_client) -> None:
    """Upsert replaces content for the same tenant/source key."""
    await ingest_chunk_async(
        async_session,
        "rag-upsert-tenant",
        "finding",
        "finding-1",
        "original text about compute",
        client=sandbox_embed_client,
    )
    await ingest_chunk_async(
        async_session,
        "rag-upsert-tenant",
        "finding",
        "finding-1",
        "updated text about storage",
        client=sandbox_embed_client,
    )
    await async_session.commit()

    count = await async_session.scalar(
        select(func.count())
        .select_from(RagChunk)
        .where(
            RagChunk.tenant_id == "rag-upsert-tenant",
            RagChunk.source_type == "finding",
            RagChunk.source_id == "finding-1",
        )
    )
    assert count == 1

    hits = await retrieve_hits_async(
        async_session,
        "rag-upsert-tenant",
        "storage",
        limit=5,
        client=sandbox_embed_client,
    )
    assert hits
    assert "updated text" in hits[0].content
    assert hits[0].score >= 0.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_source_type_filter(async_session, sandbox_embed_client) -> None:
    """source_type filter limits retrieval scope."""
    await ingest_chunk_async(
        async_session,
        "rag-filter-tenant",
        "finding",
        "f1",
        "finding chunk content",
        client=sandbox_embed_client,
    )
    await ingest_chunk_async(
        async_session,
        "rag-filter-tenant",
        "scan_summary",
        "s1",
        "summary chunk content",
        client=sandbox_embed_client,
    )
    await async_session.commit()

    hits = await retrieve_hits_async(
        async_session,
        "rag-filter-tenant",
        "chunk",
        source_type="scan_summary",
        client=sandbox_embed_client,
    )
    assert len(hits) == 1
    assert hits[0].source_type == "scan_summary"
