"""Background jobs for scan analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.ai.agent import run_finops_agent_sync
from packages.ai.llm_client import LLMClient
from packages.ai.rag import ingest_finding_chunk_sync
from packages.cloud_audit import (
    collect_config_non_compliant_rules,
    collect_security_hub_findings,
    kube_bench_json_to_findings,
    polaris_json_to_findings,
)
from packages.cloud_audit.types import NormalizedAuditFinding
from packages.core.config import get_settings
from packages.core.database_sync import sync_session_scope
from packages.core.models import Finding, Scan


def _fail_scan(scan_id: str, message: str) -> None:
    with sync_session_scope() as session:
        scan = session.scalar(select(Scan).where(Scan.id == scan_id))
        if not scan:
            return
        scan.status = "failed"
        scan.completed_at = datetime.now(UTC)
        md = dict(scan.metadata_ or {})
        md["error"] = message
        scan.metadata_ = md


def dispatch_scan(scan_id: str) -> dict[str, Any]:
    """RQ entrypoint: route work by scan_kind."""
    try:
        with sync_session_scope() as session:
            scan = session.scalar(select(Scan).where(Scan.id == scan_id))
            if not scan:
                return {"scan_id": scan_id, "status": "error", "detail": "scan not found"}
            if scan.started_at is None:
                scan.started_at = datetime.now(UTC)
            scan.status = "running"
            kind = scan.scan_kind

        if kind == "finops":
            return generate_findings(scan_id)
        if kind == "aws_audit":
            return run_aws_audit_scan(scan_id, finalize_scan=True)
        if kind == "k8s_audit":
            return run_k8s_audit_scan(scan_id)
        if kind == "combined":
            run_aws_audit_scan(scan_id, finalize_scan=False)
            return generate_findings(scan_id)
        _fail_scan(scan_id, f"unknown scan_kind: {kind}")
        return {"scan_id": scan_id, "status": "failed", "detail": "unknown scan_kind"}
    except Exception as exc:  # noqa: BLE001 — worker boundary
        _fail_scan(scan_id, str(exc))
        raise


def persist_audit_findings(session: Session, scan_id: str, items: list[NormalizedAuditFinding]) -> int:
    """Insert normalized audit rows (no FinOps RAG embedding)."""
    n = 0
    for item in items:
        session.add(
            Finding(
                scan_id=scan_id,
                finding_kind=item.finding_kind,
                framework=item.framework,
                control_id=item.control_id,
                audit_status=item.audit_status,
                title=item.title,
                category=item.category,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                estimated_savings_monthly=0.0,
                severity=item.severity,
                description=item.description,
                recommendation=item.recommendation,
                details=item.details,
            )
        )
        n += 1
    return n


def run_aws_audit_scan(scan_id: str, *, finalize_scan: bool = True) -> dict[str, Any]:
    """Security Hub + Config rule summaries → findings."""
    settings = get_settings()
    sh_raw, sh_err = collect_security_hub_findings(
        max_findings=settings.audit_security_hub_max_findings
    )
    cfg_raw, cfg_err = collect_config_non_compliant_rules(
        max_rules=settings.audit_config_max_rules
    )
    combined = list(sh_raw) + list(cfg_raw)

    with sync_session_scope() as session:
        scan = session.scalar(select(Scan).where(Scan.id == scan_id))
        if not scan:
            return {"scan_id": scan_id, "status": "error", "detail": "scan not found"}

        persist_audit_findings(session, scan_id, combined)

        md = dict(scan.metadata_ or {})
        audit_sources = dict(md.get("audit_sources") or {})
        audit_sources["security_hub"] = {"count": len(sh_raw), "error": sh_err}
        audit_sources["config"] = {"count": len(cfg_raw), "error": cfg_err}
        md["audit_sources"] = audit_sources
        scan.metadata_ = md

        if finalize_scan:
            scan.status = "completed"
            scan.completed_at = datetime.now(UTC)

    return {
        "scan_id": scan_id,
        "status": "completed" if finalize_scan else "running",
        "findings_count": len(combined),
        "security_hub_error": sh_err,
        "config_error": cfg_err,
    }


def run_k8s_audit_scan(scan_id: str) -> dict[str, Any]:
    """Load Polaris / kube-bench JSON from scan.metadata_.k8s_audit."""
    normalized: list[NormalizedAuditFinding] = []
    notes: list[str] = []
    block: dict[str, Any] = {}

    with sync_session_scope() as session:
        scan = session.scalar(select(Scan).where(Scan.id == scan_id))
        if not scan:
            return {"scan_id": scan_id, "status": "error", "detail": "scan not found"}
        meta = scan.metadata_ or {}
        raw_block = meta.get("k8s_audit")
        if isinstance(raw_block, dict):
            block = raw_block
        else:
            notes.append("missing metadata.k8s_audit object")

    polaris_payload = block.get("polaris")
    if isinstance(polaris_payload, dict):
        normalized.extend(polaris_json_to_findings(polaris_payload))
    elif polaris_payload is not None:
        notes.append("k8s_audit.polaris must be a JSON object")

    kb_payload = block.get("kube_bench")
    if isinstance(kb_payload, dict):
        normalized.extend(kube_bench_json_to_findings(kb_payload))
    elif kb_payload is not None:
        notes.append("k8s_audit.kube_bench must be a JSON object")

    with sync_session_scope() as session:
        scan = session.scalar(select(Scan).where(Scan.id == scan_id))
        if not scan:
            return {"scan_id": scan_id, "status": "error", "detail": "scan not found"}
        persist_audit_findings(session, scan_id, normalized)
        md = dict(scan.metadata_ or {})
        md["k8s_audit_ingest"] = {"notes": notes, "count": len(normalized)}
        scan.metadata_ = md
        scan.status = "completed"
        scan.completed_at = datetime.now(UTC)

    return {
        "scan_id": scan_id,
        "status": "completed",
        "findings_count": len(normalized),
        "notes": notes,
    }


def run_scan_analysis(scan_id: str, cluster_name: str | None = None) -> dict[str, Any]:
    """Run full analysis pipeline for a scan (legacy name: FinOps findings)."""
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
                finding_kind="cost",
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
