"""Normalized audit finding shared across AWS and Kubernetes collectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedAuditFinding:
    """Vendor-neutral audit row before persistence as Finding."""

    title: str
    category: str
    finding_kind: str
    framework: str
    control_id: str | None
    audit_status: str | None
    severity: str
    description: str | None
    recommendation: str | None
    resource_type: str | None
    resource_id: str | None
    details: dict[str, Any] | None
