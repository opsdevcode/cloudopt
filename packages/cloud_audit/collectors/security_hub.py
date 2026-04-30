"""Collect findings from AWS Security Hub."""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from packages.aws.client import get_securityhub_client
from packages.cloud_audit.normalize import compliance_status_to_audit, security_hub_severity
from packages.cloud_audit.types import NormalizedAuditFinding


def _pick_category(finding: dict[str, Any]) -> str:
    types = finding.get("Types") or []
    if types and isinstance(types[0], str):
        return types[0].replace("_", " ").lower()[:64]
    return "security"


def _pick_resource(finding: dict[str, Any]) -> tuple[str | None, str | None]:
    resources = finding.get("Resources") or []
    if not resources:
        return None, None
    r0 = resources[0]
    if not isinstance(r0, dict):
        return None, None
    return r0.get("Type"), r0.get("Id")


def security_hub_record_to_normalized(raw: dict[str, Any]) -> NormalizedAuditFinding:
    """Map one Security Hub Finding dict to NormalizedAuditFinding."""
    title = str(raw.get("Title") or raw.get("Id") or "Security Hub finding")[:512]
    desc = raw.get("Description")
    if isinstance(desc, str):
        description: str | None = desc
    else:
        description = None

    sev = raw.get("Severity") or {}
    severity_label = sev.get("Label") if isinstance(sev, dict) else None
    severity = security_hub_severity(
        str(severity_label) if severity_label is not None else None
    )

    compliance = raw.get("Compliance") if isinstance(raw.get("Compliance"), dict) else {}
    audit_status = compliance_status_to_audit(compliance.get("Status"))
    if audit_status is None:
        wf = raw.get("Workflow") if isinstance(raw.get("Workflow"), dict) else {}
        if str(wf.get("Status", "")).upper() in ("NEW", "NOTIFIED"):
            audit_status = "fail"

    remediation = raw.get("Remediation") or {}
    rec_text = None
    if isinstance(remediation, dict):
        rec = remediation.get("Recommendation") or {}
        if isinstance(rec, dict):
            rec_text = rec.get("Text")
            if isinstance(rec_text, str):
                pass
            else:
                rec_text = None

    rtype, rid = _pick_resource(raw)
    control_id = str(raw.get("Id") or raw.get("GeneratorId") or "")[:512] or None

    details = {
        "product_arn": raw.get("ProductArn"),
        "generator_id": raw.get("GeneratorId"),
        "aws_account_id": raw.get("AwsAccountId"),
        "record_state": raw.get("RecordState"),
        "workflow_status": (raw.get("Workflow") or {}).get("Status")
        if isinstance(raw.get("Workflow"), dict)
        else None,
    }

    return NormalizedAuditFinding(
        title=title,
        category=_pick_category(raw),
        finding_kind="security",
        framework="aws_security_hub",
        control_id=control_id,
        audit_status=audit_status,
        severity=severity,
        description=description,
        recommendation=rec_text,
        resource_type=rtype,
        resource_id=str(rid)[:255] if rid else None,
        details=details,
    )


def collect_security_hub_findings(*, max_findings: int = 500) -> tuple[list[NormalizedAuditFinding], str | None]:
    """
    List active Security Hub findings (best-effort pagination).

    Returns (findings, error_message). error_message is set on client failures.
    """
    out: list[NormalizedAuditFinding] = []
    try:
        client = get_securityhub_client()
    except Exception as exc:  # noqa: BLE001 — surface configuration errors
        return [], f"security hub client: {exc}"

    paginator = client.get_paginator("get_findings")
    try:
        for page in paginator.paginate(
            Filters={"RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]},
            PaginationConfig={"PageSize": 100},
        ):
            for raw in page.get("Findings") or []:
                if not isinstance(raw, dict):
                    continue
                out.append(security_hub_record_to_normalized(raw))
                if len(out) >= max_findings:
                    return out, None
    except ClientError as exc:
        return [], f"security hub: {exc.response.get('Error', {}).get('Message', exc)}"

    return out, None
