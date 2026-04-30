"""Tenant-scoped embedding ingest and similarity search for RAG."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from packages.ai.llm_client import AsyncLLMClient, LLMClient
from packages.core.config import get_settings
from packages.core.models import Finding, RagChunk


def _validate_embedding_dim(vec: list[float]) -> None:
    expected = get_settings().embedding_dimensions
    if len(vec) != expected:
        msg = (
            f"Embedding length {len(vec)} does not match CLOUDOPT_EMBEDDING_DIMENSIONS={expected}. "
            "Align your embed model with the DB vector column (see migration 002)."
        )
        raise ValueError(msg)


def chunk_text_for_finding(finding: Finding) -> str:
    """Flatten a finding into one embeddable string."""
    parts = [finding.title]
    if finding.description:
        parts.append(finding.description)
    if finding.recommendation:
        parts.append(finding.recommendation)
    return "\n".join(parts)


async def ingest_finding_chunk_async(
    session: AsyncSession,
    tenant_id: str,
    finding: Finding,
    *,
    client: AsyncLLMClient | None = None,
) -> RagChunk | None:
    """Embed finding text and persist a rag_chunks row (async)."""
    llm = client or AsyncLLMClient.from_settings()
    if not llm:
        return None
    content = chunk_text_for_finding(finding)
    vectors = await llm.embed([content])
    if not vectors:
        return None
    vec = vectors[0]
    _validate_embedding_dim(vec)
    row = RagChunk(
        tenant_id=tenant_id,
        source_type="finding",
        source_id=finding.id,
        content=content,
        embedding=vec,
    )
    session.add(row)
    return row


def ingest_finding_chunk_sync(
    session: Session,
    tenant_id: str,
    finding: Finding,
    *,
    client: LLMClient | None = None,
) -> RagChunk | None:
    """Embed finding text and persist a rag_chunks row (sync; RQ worker)."""
    llm = client or LLMClient.from_settings()
    if not llm:
        return None
    content = chunk_text_for_finding(finding)
    vectors = llm.embed([content])
    if not vectors:
        return None
    vec = vectors[0]
    _validate_embedding_dim(vec)
    row = RagChunk(
        tenant_id=tenant_id,
        source_type="finding",
        source_id=finding.id,
        content=content,
        embedding=vec,
    )
    session.add(row)
    return row


async def retrieve_context_async(
    session: AsyncSession,
    tenant_id: str,
    query: str,
    *,
    limit: int = 8,
    client: AsyncLLMClient | None = None,
) -> list[str]:
    """Return top-k chunk texts for tenant using cosine similarity to the query embedding."""
    llm = client or AsyncLLMClient.from_settings()
    if not llm:
        return []
    qvec = (await llm.embed([query]))[0]
    _validate_embedding_dim(qvec)
    stmt = (
        select(RagChunk)
        .where(RagChunk.tenant_id == tenant_id)
        .order_by(RagChunk.embedding.cosine_distance(qvec))
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [r.content for r in rows]


def retrieve_context_sync(
    session: Session,
    tenant_id: str,
    query: str,
    *,
    limit: int = 8,
    client: LLMClient | None = None,
) -> list[str]:
    """Sync variant for workers."""
    llm = client or LLMClient.from_settings()
    if not llm:
        return []
    qvec = llm.embed([query])[0]
    _validate_embedding_dim(qvec)
    stmt = (
        select(RagChunk)
        .where(RagChunk.tenant_id == tenant_id)
        .order_by(RagChunk.embedding.cosine_distance(qvec))
        .limit(limit)
    )
    rows = session.scalars(stmt).all()
    return [r.content for r in rows]


def format_rag_block(chunks: list[str]) -> str:
    """Join retrieved chunks for injection into prompts."""
    if not chunks:
        return ""
    lines = ["### Prior context for this account (retrieved)", ""]
    for i, c in enumerate(chunks, start=1):
        lines.append(f"{i}. {c}")
    return "\n".join(lines)


def analytics_placeholder_cur_snippet(raw: dict[str, Any]) -> str:
    """Placeholder for future CUR-derived text; keeps rag source_type contract."""
    return str(raw.get("summary", ""))[:8000]
