"""Parse kube-bench and Polaris JSON reports into normalized findings."""

from __future__ import annotations

from typing import Any

from packages.cloud_audit.types import NormalizedAuditFinding


def _polaris_severity(label: str | None) -> str:
    if not label:
        return "medium"
    s = str(label).lower()
    if s in ("danger", "critical"):
        return "high"
    if s == "warning":
        return "medium"
    return "low"


def polaris_json_to_findings(payload: dict[str, Any]) -> list[NormalizedAuditFinding]:
    """
    Parse Fairwinds Polaris audit JSON (results array or Results key).

    See https://github.com/FairwindsOps/polaris — JSON schema varies by version;
    we accept common keys: Results, ResultItems, or top-level list under \"Checks\".
    """
    out: list[NormalizedAuditFinding] = []

    candidates: list[dict[str, Any]] = []
    if isinstance(payload.get("Results"), list):
        for item in payload["Results"]:
            if isinstance(item, dict):
                candidates.append(item)
    elif isinstance(payload.get("ResultItems"), list):
        for item in payload["ResultItems"]:
            if isinstance(item, dict):
                candidates.append(item)

    for row in candidates:
        name = row.get("Name") or row.get("Check") or row.get("ID") or "polaris-check"
        msg = row.get("Message") or row.get("Title") or ""
        cat = str(row.get("Category") or "kubernetes")[0:64]
        sev = _polaris_severity(row.get("Severity"))
        ns = row.get("Namespace")
        kind = row.get("Kind")
        res_name = row.get("Name") if row.get("PodName") is None else row.get("PodName")
        rid_parts = [p for p in (ns, kind, res_name) if p]
        rid = "/".join(str(p) for p in rid_parts)[:255] if rid_parts else None

        out.append(
            NormalizedAuditFinding(
                title=str(name)[:512],
                category=cat,
                finding_kind="operational_excellence",
                framework="polaris",
                control_id=str(name)[:512],
                audit_status="fail",
                severity=sev,
                description=str(msg)[:8000] if msg else None,
                recommendation="Review Polaris documentation for this check and adjust manifests.",
                resource_type=str(kind) if kind else "Kubernetes",
                resource_id=rid,
                details={"polaris_row": row},
            )
        )

    return out


def kube_bench_json_to_findings(payload: dict[str, Any]) -> list[NormalizedAuditFinding]:
    """
    Parse kube-bench JSON output (controls with nested tests).

    Typical shape: {\"Controls\": [{\"id\": \"3.1.1\", \"tests\": [{\"desc\", \"status\"}]}]}
    """
    out: list[NormalizedAuditFinding] = []
    controls = payload.get("Controls") or payload.get("controls") or []
    if not isinstance(controls, list):
        return out

    for ctrl in controls:
        if not isinstance(ctrl, dict):
            continue
        ctrl_id = str(ctrl.get("id") or ctrl.get("section") or "control")
        tests = ctrl.get("tests") or []
        if not isinstance(tests, list):
            continue
        for test in tests:
            if not isinstance(test, dict):
                continue
            status = str(test.get("status") or "").upper()
            if status in ("PASS", "INFO", "SKIP"):
                continue
            desc = test.get("desc") or test.get("description") or ctrl_id
            test_num = test.get("test_number") or test.get("id")
            sev = "high" if status == "FAIL" else "medium"

            out.append(
                NormalizedAuditFinding(
                    title=str(desc)[:512],
                    category=str(ctrl.get("node_type") or "kubernetes")[:64],
                    finding_kind="security",
                    framework="cis_kubernetes_benchmark",
                    control_id=str(test_num or ctrl_id)[:512],
                    audit_status="fail" if status == "FAIL" else "unknown",
                    severity=sev,
                    description=str(desc),
                    recommendation="Address CIS Kubernetes Benchmark remediation for this test.",
                    resource_type="Kubernetes",
                    resource_id=None,
                    details={"control_id": ctrl_id, "test": test},
                )
            )

    return out
