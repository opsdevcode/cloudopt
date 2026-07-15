"""E2E smoke: thin Python proof against a live API (Compose stack).

Heavy orchestration (stack standup, k8s/aws/cli paths) lives in Hurl/shell — see scripts/e2e-stack-smoke.sh.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest

from packages.cloud_audit.types import NormalizedAuditFinding
from tests.helpers.scans import wait_for_scan_async

MOCK_AWS_FINDINGS = [
    NormalizedAuditFinding(
        title="Mock Security Hub finding",
        category="security",
        finding_kind="security",
        framework="aws_security_hub",
        control_id="SH-1",
        audit_status="fail",
        severity="high",
        description="E2E stub",
        recommendation="Review",
        resource_type="AwsAccount",
        resource_id="123456789012",
        details={},
    )
]


def _live_api_base() -> str:
    base = os.environ.get("CLOUDOPT_E2E_LIVE_API", os.environ.get("CLOUDOPT_API_BASE_URL", ""))
    if not base:
        pytest.skip("live API e2e: set CLOUDOPT_E2E_LIVE_API (e.g. http://127.0.0.1:8000)")
    return base.rstrip("/")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_finops_scan_completes_live_api() -> None:
    """One Python smoke: finops scan completes via real stack (api + worker + redis)."""
    base = _live_api_base()
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        ready = await client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"

        create = await client.post(
            "/api/v1/scans",
            json={"scan_kind": "finops", "tenant_id": "py-e2e-finops"},
        )
        assert create.status_code == 200
        scan_id = create.json()["id"]

        done = await wait_for_scan_async(client, scan_id, timeout=90)
        assert done["status"] == "completed"

        summary = await client.get(f"/api/v1/scans/{scan_id}/summary")
        assert summary.status_code == 200
        assert summary.json()["findings_total"] > 0


@pytest.mark.integration
def test_aws_audit_persists_mock_findings_inprocess() -> None:
    """aws_audit worker path with collectors stubbed (in-process, no RQ)."""
    from apps.worker import jobs
    from packages.core.database_sync import sync_session_scope
    from packages.core.models import Scan

    with (
        patch(
            "apps.worker.jobs.collect_security_hub_findings",
            return_value=(MOCK_AWS_FINDINGS, None),
        ),
        patch(
            "apps.worker.jobs.collect_config_non_compliant_rules",
            return_value=([], None),
        ),
    ):
        with sync_session_scope() as session:
            scan = Scan(tenant_id="e2e-aws-inprocess", scan_kind="aws_audit", status="pending")
            session.add(scan)
            session.flush()
            scan_id = scan.id

        result = jobs.run_aws_audit_scan(scan_id)
        assert result["status"] == "completed"
        assert result["findings_count"] >= 1
