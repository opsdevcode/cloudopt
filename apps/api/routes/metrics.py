"""Aggregate metrics for dashboard overview."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Finding, Scan

router = APIRouter()


class RecentScanBrief(BaseModel):
    """Minimal scan row for overview lists."""

    id: str
    tenant_id: str
    scan_kind: str
    status: str
    cluster_name: str | None
    created_at: str


class OverviewMetricsResponse(BaseModel):
    """Cross-scan aggregates for the UI overview."""

    findings_total: int
    estimated_savings_monthly_total: float
    findings_by_severity: dict[str, int]
    findings_by_finding_kind: dict[str, int]
    scans_total: int
    scans_by_status: dict[str, int]
    recent_scans: list[RecentScanBrief]


@router.get("/overview", response_model=OverviewMetricsResponse)
async def get_overview_metrics(
    db: AsyncSession = Depends(get_db),
    recent_limit: int = 15,
):
    """Roll-up counts and recent scans for dashboard home."""
    findings_total = int(
        (await db.execute(select(func.count(Finding.id)))).scalar_one(),
    )
    savings_raw = (
        await db.execute(select(func.coalesce(func.sum(Finding.estimated_savings_monthly), 0.0)))
    ).scalar_one()
    estimated_savings_monthly_total = float(savings_raw or 0.0)

    sev_rows = (
        await db.execute(
            select(Finding.severity, func.count(Finding.id)).group_by(Finding.severity),
        )
    ).all()
    kind_rows = (
        await db.execute(
            select(Finding.finding_kind, func.count(Finding.id)).group_by(Finding.finding_kind),
        )
    ).all()
    findings_by_severity = {str(k): int(v) for k, v in sev_rows}
    findings_by_finding_kind = {str(k): int(v) for k, v in kind_rows}

    scans_total = int((await db.execute(select(func.count(Scan.id)))).scalar_one())
    status_rows = (
        await db.execute(select(Scan.status, func.count(Scan.id)).group_by(Scan.status))
    ).all()
    scans_by_status = {str(k): int(v) for k, v in status_rows}

    recent_result = await db.execute(
        select(Scan).order_by(Scan.created_at.desc()).limit(max(1, min(recent_limit, 50))),
    )
    recent_scans = [
        RecentScanBrief(
            id=s.id,
            tenant_id=s.tenant_id,
            scan_kind=s.scan_kind,
            status=s.status,
            cluster_name=s.cluster_name,
            created_at=s.created_at.isoformat(),
        )
        for s in recent_result.scalars().all()
    ]

    return OverviewMetricsResponse(
        findings_total=findings_total,
        estimated_savings_monthly_total=estimated_savings_monthly_total,
        findings_by_severity=findings_by_severity,
        findings_by_finding_kind=findings_by_finding_kind,
        scans_total=scans_total,
        scans_by_status=scans_by_status,
        recent_scans=recent_scans,
    )
