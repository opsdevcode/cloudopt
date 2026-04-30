"""FinOps agent tools: DB queries and cost/spike helpers (Phase C)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.ai.analyzer import analyze_cost_spike
from packages.core.models import Finding, Scan

# OpenAI-compatible tool definitions (function calling).
FINOPS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_recent_findings",
            "description": (
                "List recent cost findings for this tenant across scans "
                "(titles, categories, savings estimates). Use for historical patterns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum findings to return (1–50).",
                        "default": 15,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scan_snapshot",
            "description": (
                "Load the current scan row (status, cluster, metadata) and summaries "
                "of findings already attached to that scan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scan_id": {
                        "type": "string",
                        "description": "Scan UUID; omit to use the scan from session context.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_cost_metadata",
            "description": (
                "Billing context for the scan: CUR/Cost Explorer ingestion status and "
                "any cost hints stored on the scan metadata (placeholder until full ingestion)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "range_days": {
                        "type": "integer",
                        "description": "Observation window in days (informational).",
                        "default": 30,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_cost_spike",
            "description": (
                "Structured spike analysis stub using scan metadata and optional focus notes "
                "(replace with real anomaly detection when billing signals are wired)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "Optional hypothesis or dimension (e.g. EC2, data transfer).",
                    },
                },
            },
        },
    },
]


def _clamp_limit(raw: Any, default: int = 15, *, lo: int = 1, hi: int = 50) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def _tool_query_recent_findings(
    session: Session,
    tenant_id: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    limit = _clamp_limit(args.get("limit"), default=15)
    stmt = (
        select(Finding, Scan.cluster_name)
        .join(Scan, Finding.scan_id == Scan.id)
        .where(Scan.tenant_id == tenant_id)
        .order_by(Finding.created_at.desc())
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    items: list[dict[str, Any]] = []
    for finding, cluster_name in rows:
        items.append(
            {
                "finding_id": finding.id,
                "scan_id": finding.scan_id,
                "cluster_name": cluster_name,
                "title": finding.title,
                "category": finding.category,
                "severity": finding.severity,
                "estimated_savings_monthly": finding.estimated_savings_monthly,
                "resource_type": finding.resource_type,
                "resource_id": finding.resource_id,
            }
        )
    return {"count": len(items), "findings": items}


def _tool_get_scan_snapshot(
    session: Session,
    tenant_id: str,
    scan_id: str | None,
    args: dict[str, Any],
) -> dict[str, Any]:
    sid = args.get("scan_id")
    resolved: str | None = sid.strip() if isinstance(sid, str) and sid.strip() else scan_id
    if not resolved:
        return {"error": "scan_id required (from context or arguments)"}
    scan = session.scalar(select(Scan).where(Scan.id == resolved, Scan.tenant_id == tenant_id))
    if not scan:
        return {"error": "scan not found for tenant"}
    findings = session.scalars(select(Finding).where(Finding.scan_id == resolved)).all()
    return {
        "scan": {
            "id": scan.id,
            "status": scan.status,
            "cluster_name": scan.cluster_name,
            "metadata": scan.metadata_ or {},
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        },
        "existing_findings_count": len(findings),
        "existing_findings": [
            {
                "title": f.title,
                "category": f.category,
                "severity": f.severity,
                "estimated_savings_monthly": f.estimated_savings_monthly,
            }
            for f in findings
        ],
    }


def _tool_fetch_cost_metadata(
    session: Session,
    tenant_id: str,
    scan_id: str | None,
    args: dict[str, Any],
) -> dict[str, Any]:
    range_days = 30
    try:
        range_days = int(args.get("range_days", 30))
    except (TypeError, ValueError):
        range_days = 30
    range_days = max(1, min(365, range_days))

    meta: dict[str, Any] = {}
    if scan_id:
        scan = session.scalar(select(Scan).where(Scan.id == scan_id, Scan.tenant_id == tenant_id))
        if scan and scan.metadata_:
            meta = dict(scan.metadata_)
    cost_hints = meta.get("cost_hints") or meta.get("cost_explorer") or meta.get("cur")
    return {
        "ingestion": "placeholder",
        "note": (
            "Full CUR/Cost Explorer ingestion is not wired in this build; "
            "values below come only from scan metadata when present."
        ),
        "range_days": range_days,
        "hints_from_scan_metadata": cost_hints,
    }


def _tool_explain_cost_spike(
    session: Session,
    tenant_id: str,
    scan_id: str | None,
    args: dict[str, Any],
) -> dict[str, Any]:
    focus = args.get("focus")
    raw: dict[str, Any] = {"note": "spike helper"}
    if isinstance(focus, str) and focus.strip():
        raw["focus"] = focus.strip()
    if scan_id:
        scan = session.scalar(select(Scan).where(Scan.id == scan_id, Scan.tenant_id == tenant_id))
        if scan and scan.metadata_:
            raw["scan_metadata"] = scan.metadata_
    return analyze_cost_spike(raw)


def execute_finops_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    session: Session,
    tenant_id: str,
    scan_id: str | None,
) -> str:
    """Run a whitelisted tool and return JSON text for the assistant."""
    handlers: dict[str, Any] = {
        "query_recent_findings": lambda: _tool_query_recent_findings(session, tenant_id, arguments),
        "get_scan_snapshot": lambda: _tool_get_scan_snapshot(
            session, tenant_id, scan_id, arguments
        ),
        "fetch_cost_metadata": lambda: _tool_fetch_cost_metadata(
            session, tenant_id, scan_id, arguments
        ),
        "explain_cost_spike": lambda: _tool_explain_cost_spike(
            session, tenant_id, scan_id, arguments
        ),
    }
    fn = handlers.get(name)
    if not fn:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        payload = fn()
    except Exception as exc:  # noqa: BLE001 — tool boundary; return error JSON
        return json.dumps({"error": type(exc).__name__, "message": str(exc)})
    return json.dumps(payload, default=str)
