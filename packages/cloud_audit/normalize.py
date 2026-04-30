"""Map vendor-specific labels to CloudOpt Finding fields."""

from __future__ import annotations


def security_hub_severity(label: str | None) -> str:
    """Map Security Hub Severity.Label to Finding.severity."""
    if not label:
        return "medium"
    u = str(label).upper()
    if u in ("CRITICAL", "HIGH"):
        return "high"
    if u == "MEDIUM":
        return "medium"
    return "low"


def compliance_status_to_audit(status: str | None) -> str | None:
    """Normalize Compliance.Status strings."""
    if not status:
        return None
    return str(status).lower()
