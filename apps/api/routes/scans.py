"""Scans API."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.job_queue import enqueue_dispatch_scan
from packages.core.models import Finding, Scan

router = APIRouter()

SCAN_KINDS = frozenset({"finops", "aws_audit", "k8s_audit", "combined"})


class ScanCreate(BaseModel):
    """Request body for creating a scan."""

    cluster_name: str | None = None
    tenant_id: str = "default"
    scan_kind: str = Field(
        default="finops",
        description="finops | aws_audit | k8s_audit | combined",
    )
    metadata: dict[str, Any] | None = None


class ScanResponse(BaseModel):
    """Scan response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    scan_kind: str
    status: str
    cluster_name: str | None
    metadata: dict[str, Any] | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str | None = None


def _scan_to_response(scan: Scan) -> ScanResponse:
    return ScanResponse(
        id=scan.id,
        tenant_id=scan.tenant_id,
        scan_kind=scan.scan_kind,
        status=scan.status,
        cluster_name=scan.cluster_name,
        metadata=scan.metadata_,
        created_at=scan.created_at.isoformat(),
        started_at=scan.started_at.isoformat() if scan.started_at else None,
        completed_at=scan.completed_at.isoformat() if scan.completed_at else None,
        updated_at=scan.updated_at.isoformat() if scan.updated_at else None,
    )


class ScanSummaryResponse(BaseModel):
    """Aggregated counts for a scan's findings."""

    scan_id: str
    scan_kind: str
    status: str
    findings_total: int
    by_severity: dict[str, int]
    by_finding_kind: dict[str, int]


@router.post("", response_model=ScanResponse)
async def create_scan(
    body: ScanCreate | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan and enqueue background analysis."""
    payload = body or ScanCreate()
    kind = payload.scan_kind
    if kind not in SCAN_KINDS:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Invalid scan_kind; allowed: {sorted(SCAN_KINDS)}",
        )
    scan = Scan(
        tenant_id=payload.tenant_id,
        scan_kind=kind,
        status="pending",
        cluster_name=payload.cluster_name,
        metadata_=payload.metadata,
    )
    db.add(scan)
    await db.flush()
    await db.refresh(scan)
    enqueue_dispatch_scan(scan.id)
    return _scan_to_response(scan)


@router.get("", response_model=list[ScanResponse])
async def list_scans(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """List recent scans."""
    result = await db.execute(select(Scan).order_by(Scan.created_at.desc()).limit(limit))
    scans = result.scalars().all()
    return [_scan_to_response(s) for s in scans]


@router.get("/{scan_id}/summary", response_model=ScanSummaryResponse)
async def get_scan_summary(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Counts of findings by severity and finding_kind for one scan."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Scan not found")

    sev_stmt = (
        select(Finding.severity, func.count(Finding.id))
        .where(Finding.scan_id == scan_id)
        .group_by(Finding.severity)
    )
    kind_stmt = (
        select(Finding.finding_kind, func.count(Finding.id))
        .where(Finding.scan_id == scan_id)
        .group_by(Finding.finding_kind)
    )
    total_stmt = select(func.count(Finding.id)).where(Finding.scan_id == scan_id)

    sev_rows = (await db.execute(sev_stmt)).all()
    kind_rows = (await db.execute(kind_stmt)).all()
    by_severity: dict[str, int] = {str(k): int(v) for k, v in sev_rows}
    by_finding_kind: dict[str, int] = {str(k): int(v) for k, v in kind_rows}
    total = (await db.execute(total_stmt)).scalar_one()

    return ScanSummaryResponse(
        scan_id=scan.id,
        scan_kind=scan.scan_kind,
        status=scan.status,
        findings_total=int(total),
        by_severity=by_severity,
        by_finding_kind=by_finding_kind,
    )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a scan by ID."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_to_response(scan)
