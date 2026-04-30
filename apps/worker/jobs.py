"""Background jobs for scan analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from packages.ai.agent import run_finops_agent_sync
from packages.ai.llm_client import LLMClient
from packages.ai.rag import ingest_finding_chunk_sync
from packages.core.database_sync import sync_session_scope
from packages.core.models import Finding, Scan


def run_scan_analysis(scan_id: str, cluster_name: str | None = None) -> dict[str, Any]:
    """Run full analysis pipeline for a scan (currently: generate findings)."""
    return generate_findings(scan_id)


def ingest_aws_costs(scan_id: str, range_days: int = 30) -> dict[str, Any]:
    """Ingest AWS Cost Explorer / CUR data for scan (placeholder)."""
    return {"scan_id": scan_id, "status": "placeholder", "range_days": range_days}


def generate_findings(scan_id: str) -> dict[str, Any]:
    """
    Run FinOps agent + LLM (when configured), persist findings, and index chunks for RAG.
    """
    with sync_session_scope() as session:
        scan = session.scalar(select(Scan).where(Scan.id == scan_id))
        if not scan:
            return {"scan_id": scan_id, "status": "error", "detail": "scan not found"}

        if scan.started_at is None:
            scan.started_at = datetime.now(UTC)

        context: dict[str, Any] = {
            "scan_id": scan.id,
            "tenant_id": scan.tenant_id,
            "cluster_name": scan.cluster_name,
            "metadata": scan.metadata_ or {},
            "rag_query": f"cost optimization kubernetes AWS {scan.cluster_name or ''}".strip(),
        }

        result = run_finops_agent_sync(session, scan.tenant_id, context)

        created: list[Finding] = []
        for payload in result.get("findings", []):
            finding = Finding(
                scan_id=scan.id,
                title=payload["title"],
                category=payload["category"],
                resource_type=payload.get("resource_type"),
                resource_id=payload.get("resource_id"),
                estimated_savings_monthly=float(payload.get("estimated_savings_monthly") or 0.0),
                severity=payload.get("severity") or "medium",
                description=payload.get("description"),
                recommendation=payload.get("recommendation"),
            )
            session.add(finding)
            created.append(finding)

        session.flush()

        llm = LLMClient.from_settings()
        if llm:
            for finding in created:
                ingest_finding_chunk_sync(session, scan.tenant_id, finding, client=llm)

        scan.status = "completed"
        scan.completed_at = datetime.now(UTC)

        return {
            "scan_id": scan_id,
            "status": scan.status,
            "findings_count": len(created),
            "summary": result.get("summary", ""),
        }
