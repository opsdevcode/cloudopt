"""FinOps domain types (non-DB). Placeholder for cost/finding DTOs."""

from typing import Any

from pydantic import BaseModel


class FindingSummary(BaseModel):
    """Summary of a single cost optimization finding."""

    id: str
    title: str
    category: str
    estimated_savings_monthly: float
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] | None = None


class ScanSummary(BaseModel):
    """Summary of a scan run."""

    id: str
    status: str
    findings_count: int
    total_potential_savings_monthly: float
