"""RAG unit tests (no Postgres required)."""

from __future__ import annotations

from packages.ai.rag import (
    RagHit,
    chunk_text_for_finding,
    format_rag_block,
    select_audit_findings_for_embed,
)
from packages.core.models import Finding


def test_format_rag_block_with_hits() -> None:
    hits = [
        RagHit(content="alpha", source_type="finding", source_id="f1", score=0.9),
        RagHit(content="beta", source_type="scan_summary", source_id="s1", score=0.8),
    ]
    text = format_rag_block(hits)
    assert "Prior context" in text
    assert "alpha" in text and "beta" in text


def test_chunk_text_for_finding() -> None:
    finding = Finding(
        scan_id="scan-1",
        title="Idle EBS volume",
        description="Volume unused 90 days",
        recommendation="Delete or snapshot",
    )
    text = chunk_text_for_finding(finding)
    assert "Idle EBS volume" in text
    assert "Delete or snapshot" in text


def test_select_audit_findings_for_embed_orders_by_severity() -> None:
    findings = [
        Finding(scan_id="s", title="low", category="sec", severity="low"),
        Finding(scan_id="s", title="high", category="sec", severity="high"),
        Finding(scan_id="s", title="critical", category="sec", severity="critical"),
    ]
    selected = select_audit_findings_for_embed(findings, max_chunks=2)
    assert [f.severity for f in selected] == ["critical", "high"]
