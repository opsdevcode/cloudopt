"""Scans API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database import get_db
from packages.core.models import Scan

router = APIRouter()


class ScanCreate(BaseModel):
    """Request body for creating a scan."""

    cluster_name: str | None = None
    tenant_id: str = "default"


class ScanResponse(BaseModel):
    """Scan response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    status: str
    cluster_name: str | None
    created_at: str


@router.post("", response_model=ScanResponse)
async def create_scan(
    body: ScanCreate | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan (placeholder: enqueue job in worker TBD)."""
    scan = Scan(
        tenant_id=body.tenant_id if body else "default",
        status="pending",
        cluster_name=body.cluster_name if body else None,
    )
    db.add(scan)
    await db.flush()
    await db.refresh(scan)
    return ScanResponse(
        id=scan.id,
        tenant_id=scan.tenant_id,
        status=scan.status,
        cluster_name=scan.cluster_name,
        created_at=scan.created_at.isoformat(),
    )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a scan by ID."""
    from sqlalchemy import select

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse(
        id=scan.id,
        tenant_id=scan.tenant_id,
        status=scan.status,
        cluster_name=scan.cluster_name,
        created_at=scan.created_at.isoformat(),
    )


@router.get("", response_model=list[ScanResponse])
async def list_scans(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """List recent scans."""
    from sqlalchemy import select

    result = await db.execute(select(Scan).order_by(Scan.created_at.desc()).limit(limit))
    scans = result.scalars().all()
    return [
        ScanResponse(
            id=s.id,
            tenant_id=s.tenant_id,
            status=s.status,
            cluster_name=s.cluster_name,
            created_at=s.created_at.isoformat(),
        )
        for s in scans
    ]
