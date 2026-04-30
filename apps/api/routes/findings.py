"""Findings API."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Finding, Scan

router = APIRouter()


class FindingResponse(BaseModel):
    """Finding response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    finding_kind: str
    framework: str | None
    control_id: str | None
    audit_status: str | None
    title: str
    category: str
    resource_type: str | None
    resource_id: str | None
    estimated_savings_monthly: float
    severity: str
    description: str | None
    recommendation: str | None
    details: dict | None
    created_at: str


@router.get("", response_model=list[FindingResponse])
async def list_findings(
    db: AsyncSession = Depends(get_db),
    scan_id: str | None = Query(None, description="Filter by scan ID"),
    scan_kind: str | None = Query(None, description="Filter by parent scan kind"),
    finding_kind: str | None = Query(None, description="Filter by finding_kind"),
    framework: str | None = Query(None, description="Filter by framework prefix"),
    limit: int = Query(100, le=500),
):
    """List findings with optional filters."""
    q = select(Finding).order_by(Finding.created_at.desc()).limit(limit)
    if scan_id:
        q = q.where(Finding.scan_id == scan_id)
    if scan_kind is not None:
        q = q.join(Scan, Finding.scan_id == Scan.id).where(Scan.scan_kind == scan_kind)
    if finding_kind:
        q = q.where(Finding.finding_kind == finding_kind)
    if framework:
        q = q.where(Finding.framework.startswith(framework))
    result = await db.execute(q)
    findings = result.scalars().all()
    return [
        FindingResponse(
            id=f.id,
            scan_id=f.scan_id,
            finding_kind=f.finding_kind,
            framework=f.framework,
            control_id=f.control_id,
            audit_status=f.audit_status,
            title=f.title,
            category=f.category,
            resource_type=f.resource_type,
            resource_id=f.resource_id,
            estimated_savings_monthly=f.estimated_savings_monthly,
            severity=f.severity,
            description=f.description,
            recommendation=f.recommendation,
            details=f.details,
            created_at=f.created_at.isoformat(),
        )
        for f in findings
    ]


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a finding by ID."""
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingResponse(
        id=finding.id,
        scan_id=finding.scan_id,
        finding_kind=finding.finding_kind,
        framework=finding.framework,
        control_id=finding.control_id,
        audit_status=finding.audit_status,
        title=finding.title,
        category=finding.category,
        resource_type=finding.resource_type,
        resource_id=finding.resource_id,
        estimated_savings_monthly=finding.estimated_savings_monthly,
        severity=finding.severity,
        description=finding.description,
        recommendation=finding.recommendation,
        details=finding.details,
        created_at=finding.created_at.isoformat(),
    )
