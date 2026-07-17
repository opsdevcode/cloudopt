"""Tenant-scoped embedding ingest and similarity search for RAG."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from packages.ai.llm_client import (
    AsyncChatClient,
    AsyncLLMClient,
    LLMClient,
    SyncChatClient,
)
from packages.core.config import get_settings
from packages.core.models import Finding, RagChunk, Scan, uuid_str


@dataclass(frozen=True)
class RagHit:
    """One retrieved chunk with similarity metadata."""

    content: str
    source_type: str
    source_id: str | None
    score: float


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


def chunk_text_for_scan_summary(scan: Scan, summary: str, findings_count: int) -> str:
    """Build embeddable scan summary text."""
    parts = [
        f"Scan kind: {scan.scan_kind}",
        f"Scan id: {scan.id}",
        f"Cluster: {scan.cluster_name or 'n/a'}",
        f"Findings count: {findings_count}",
        summary.strip() or "No agent summary.",
    ]
    return "\n".join(parts)


async def upsert_chunk_async(
    session: AsyncSession,
    tenant_id: str,
    source_type: str,
    source_id: str,
    content: str,
    vec: list[float],
) -> RagChunk:
    """Insert or replace a rag_chunks row keyed by tenant + source."""
    now = datetime.now(UTC)
    stmt = (
        pg_insert(RagChunk)
        .values(
            id=uuid_str(),
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
            embedding=vec,
            created_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_rag_chunks_tenant_source",
            set_={
                "content": content,
                "embedding": vec,
                "created_at": now,
            },
        )
        .returning(RagChunk)
    )
    result = await session.execute(stmt)
    row = result.scalar_one()
    return row


def upsert_chunk_sync(
    session: Session,
    tenant_id: str,
    source_type: str,
    source_id: str,
    content: str,
    vec: list[float],
) -> RagChunk:
    """Sync upsert for RQ worker."""
    now = datetime.now(UTC)
    stmt = (
        pg_insert(RagChunk)
        .values(
            id=uuid_str(),
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            content=content,
            embedding=vec,
            created_at=now,
        )
        .on_conflict_do_update(
            constraint="uq_rag_chunks_tenant_source",
            set_={
                "content": content,
                "embedding": vec,
                "created_at": now,
            },
        )
        .returning(RagChunk)
    )
    result = session.execute(stmt)
    return result.scalar_one()


async def ingest_chunk_async(
    session: AsyncSession,
    tenant_id: str,
    source_type: str,
    source_id: str,
    content: str,
    *,
    client: AsyncChatClient | None = None,
) -> RagChunk | None:
    """Embed text and upsert a rag_chunks row (async)."""
    llm = client or AsyncLLMClient.from_settings()
    if not llm:
        return None
    vectors = await llm.embed([content])
    if not vectors:
        return None
    vec = vectors[0]
    _validate_embedding_dim(vec)
    return await upsert_chunk_async(session, tenant_id, source_type, source_id, content, vec)


def ingest_chunk_sync(
    session: Session,
    tenant_id: str,
    source_type: str,
    source_id: str,
    content: str,
    *,
    client: SyncChatClient | None = None,
) -> RagChunk | None:
    """Embed text and upsert a rag_chunks row (sync; RQ worker)."""
    llm = client or LLMClient.from_settings()
    if not llm:
        return None
    vectors = llm.embed([content])
    if not vectors:
        return None
    vec = vectors[0]
    _validate_embedding_dim(vec)
    return upsert_chunk_sync(session, tenant_id, source_type, source_id, content, vec)


async def ingest_finding_chunk_async(
    session: AsyncSession,
    tenant_id: str,
    finding: Finding,
    *,
    client: AsyncChatClient | None = None,
) -> RagChunk | None:
    """Embed finding text and upsert a rag_chunks row (async)."""
    return await ingest_chunk_async(
        session,
        tenant_id,
        "finding",
        finding.id,
        chunk_text_for_finding(finding),
        client=client,
    )


def ingest_finding_chunk_sync(
    session: Session,
    tenant_id: str,
    finding: Finding,
    *,
    client: SyncChatClient | None = None,
) -> RagChunk | None:
    """Embed finding text and upsert a rag_chunks row (sync; RQ worker)."""
    return ingest_chunk_sync(
        session,
        tenant_id,
        "finding",
        finding.id,
        chunk_text_for_finding(finding),
        client=client,
    )


def ingest_scan_summary_sync(
    session: Session,
    scan: Scan,
    summary: str,
    findings_count: int,
    *,
    client: SyncChatClient | None = None,
) -> RagChunk | None:
    """Embed scan summary for cross-scan retrieval."""
    content = chunk_text_for_scan_summary(scan, summary, findings_count)
    return ingest_chunk_sync(
        session,
        scan.tenant_id,
        "scan_summary",
        scan.id,
        content,
        client=client,
    )


def _apply_rag_filters(
    stmt: Any,
    *,
    tenant_id: str,
    source_type: str | None,
    scan_id: str | None,
) -> Any:
    stmt = stmt.where(RagChunk.tenant_id == tenant_id)
    if source_type:
        stmt = stmt.where(RagChunk.source_type == source_type)
    if scan_id:
        finding_ids = select(Finding.id).where(Finding.scan_id == scan_id)
        stmt = stmt.where(
            or_(
                and_(RagChunk.source_type == "scan_summary", RagChunk.source_id == scan_id),
                and_(RagChunk.source_type == "finding", RagChunk.source_id.in_(finding_ids)),
            )
        )
    return stmt


async def retrieve_hits_async(
    session: AsyncSession,
    tenant_id: str,
    query: str,
    *,
    limit: int = 8,
    source_type: str | None = None,
    scan_id: str | None = None,
    client: AsyncChatClient | None = None,
) -> list[RagHit]:
    """Return top-k chunks with scores for tenant using cosine similarity."""
    llm = client or AsyncLLMClient.from_settings()
    if not llm:
        return []
    qvec = (await llm.embed([query]))[0]
    _validate_embedding_dim(qvec)
    distance = RagChunk.embedding.cosine_distance(qvec).label("distance")
    stmt = select(RagChunk, distance)
    stmt = _apply_rag_filters(stmt, tenant_id=tenant_id, source_type=source_type, scan_id=scan_id)
    stmt = stmt.order_by(distance).limit(limit)
    result = await session.execute(stmt)
    hits: list[RagHit] = []
    for row, dist in result.all():
        hits.append(
            RagHit(
                content=row.content,
                source_type=row.source_type,
                source_id=row.source_id,
                score=max(0.0, 1.0 - float(dist)),
            )
        )
    return hits


def retrieve_hits_sync(
    session: Session,
    tenant_id: str,
    query: str,
    *,
    limit: int = 8,
    source_type: str | None = None,
    scan_id: str | None = None,
    client: SyncChatClient | None = None,
) -> list[RagHit]:
    """Sync variant for workers."""
    llm = client or LLMClient.from_settings()
    if not llm:
        return []
    qvec = llm.embed([query])[0]
    _validate_embedding_dim(qvec)
    distance = RagChunk.embedding.cosine_distance(qvec).label("distance")
    stmt = select(RagChunk, distance)
    stmt = _apply_rag_filters(stmt, tenant_id=tenant_id, source_type=source_type, scan_id=scan_id)
    stmt = stmt.order_by(distance).limit(limit)
    hits: list[RagHit] = []
    for row, dist in session.execute(stmt).all():
        hits.append(
            RagHit(
                content=row.content,
                source_type=row.source_type,
                source_id=row.source_id,
                score=max(0.0, 1.0 - float(dist)),
            )
        )
    return hits


async def retrieve_context_async(
    session: AsyncSession,
    tenant_id: str,
    query: str,
    *,
    limit: int = 8,
    source_type: str | None = None,
    scan_id: str | None = None,
    client: AsyncChatClient | None = None,
) -> list[str]:
    """Return top-k chunk texts (backward-compatible helper)."""
    hits = await retrieve_hits_async(
        session,
        tenant_id,
        query,
        limit=limit,
        source_type=source_type,
        scan_id=scan_id,
        client=client,
    )
    return [h.content for h in hits]


def retrieve_context_sync(
    session: Session,
    tenant_id: str,
    query: str,
    *,
    limit: int = 8,
    source_type: str | None = None,
    scan_id: str | None = None,
    client: SyncChatClient | None = None,
) -> list[str]:
    """Sync variant returning chunk text only."""
    hits = retrieve_hits_sync(
        session,
        tenant_id,
        query,
        limit=limit,
        source_type=source_type,
        scan_id=scan_id,
        client=client,
    )
    return [h.content for h in hits]


def format_rag_block(chunks: list[str] | list[RagHit]) -> str:
    """Join retrieved chunks for injection into prompts."""
    if not chunks:
        return ""
    texts = [c if isinstance(c, str) else c.content for c in chunks]
    lines = ["### Prior context for this account (retrieved)", ""]
    for i, c in enumerate(texts, start=1):
        lines.append(f"{i}. {c}")
    return "\n".join(lines)


def analytics_placeholder_cur_snippet(raw: dict[str, Any]) -> str:
    """Placeholder for future CUR-derived text; keeps rag source_type contract."""
    return str(raw.get("summary", ""))[:8000]


_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def select_audit_findings_for_embed(findings: list[Finding], max_chunks: int) -> list[Finding]:
    """Pick highest-severity audit findings up to max_chunks."""
    ranked = sorted(
        findings,
        key=lambda f: (_SEVERITY_RANK.get(f.severity.lower(), 99), f.title),
    )
    return ranked[: max(0, max_chunks)]


def embed_audit_findings_sync(
    session: Session,
    tenant_id: str,
    findings: list[Finding],
    *,
    client: SyncChatClient | None,
    max_chunks: int,
) -> int:
    """Optionally embed top audit findings (cost-controlled)."""
    selected = select_audit_findings_for_embed(findings, max_chunks)
    n = 0
    for finding in selected:
        if ingest_finding_chunk_sync(session, tenant_id, finding, client=client):
            n += 1
    return n
