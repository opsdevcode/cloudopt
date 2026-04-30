"""cloudopt audit — AWS and Kubernetes posture scans via API."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

import httpx
import typer

from packages.core.config import get_settings

audit_app = typer.Typer(help="Run cloud posture audits (requires API + worker).")


def _wait_scan(client: httpx.Client, base: str, scan_id: str, timeout_s: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        r = client.get(f"{base}/api/v1/scans/{scan_id}")
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, dict) and payload.get("status") in ("completed", "failed"):
            return cast(dict[str, Any], payload)
        time.sleep(2)
    raise typer.BadParameter(f"Scan {scan_id} did not finish within {timeout_s}s")


def _print_findings_text(rows: list[dict[str, Any]]) -> None:
    typer.echo("")
    typer.echo(f"Findings ({len(rows)})")
    typer.echo("=" * 48)
    for row in rows:
        typer.echo(f"[{row.get('severity')}] {row.get('title')}")
        typer.echo(f"  kind={row.get('finding_kind')} framework={row.get('framework')}")
        if row.get("resource_id"):
            typer.echo(f"  resource: {row.get('resource_id')}")
        typer.echo("")


def _emit_audit_json(
    client: httpx.Client,
    base: str,
    scan_id: str,
    done: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    """Emit scan + summary + findings as one JSON document (--output json)."""
    summary = None
    sr = client.get(f"{base}/api/v1/scans/{scan_id}/summary")
    if sr.is_success:
        summary = sr.json()
    typer.echo(json.dumps({"scan": done, "summary": summary, "findings": findings}, indent=2))


@audit_app.command("aws")
def audit_aws(
    tenant: str = typer.Option("default", "--tenant", "-t"),
    cluster: str | None = typer.Option(None, "--cluster", "-c"),
    output: str = typer.Option("text", "--output", "-o", help="text or json"),
    wait_timeout: int = typer.Option(300, "--timeout", help="Seconds to wait for scan."),
) -> None:
    """Create an aws_audit scan and print findings."""
    settings = get_settings()
    base = settings.api_base_url
    payload: dict[str, Any] = {"tenant_id": tenant, "scan_kind": "aws_audit"}
    if cluster:
        payload["cluster_name"] = cluster

    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{base}/api/v1/scans", json=payload)
        r.raise_for_status()
        scan = r.json()
        scan_id = scan["id"]
        typer.echo(f"Scan {scan_id} ({scan['scan_kind']}) status={scan['status']}")

        done = _wait_scan(client, base, scan_id, wait_timeout)
        typer.echo(f"Final status: {done['status']}")

        fr = client.get(f"{base}/api/v1/findings", params={"scan_id": scan_id, "limit": 500})
        fr.raise_for_status()
        findings = fr.json()

        if output == "json":
            _emit_audit_json(client, base, scan_id, done, findings)
            return

    _print_findings_text(findings)


@audit_app.command("k8s")
def audit_k8s(
    tenant: str = typer.Option("default", "--tenant", "-t"),
    polaris_json: Path | None = typer.Option(
        None,
        "--polaris-json",
        help="Path to Polaris JSON report to send in scan metadata.",
    ),
    kube_bench_json: Path | None = typer.Option(
        None,
        "--kube-bench-json",
        help="Path to kube-bench JSON output (e.g. kube-bench json).",
    ),
    cluster: str | None = typer.Option(None, "--cluster", "-c"),
    output: str = typer.Option("text", "--output", "-o", help="text or json"),
    wait_timeout: int = typer.Option(120, "--timeout", help="Seconds to wait for scan."),
) -> None:
    """Create a k8s_audit scan using Polaris and/or kube-bench JSON from files."""
    if not polaris_json and not kube_bench_json:
        raise typer.BadParameter("Provide --polaris-json and/or --kube-bench-json")

    settings = get_settings()
    base = settings.api_base_url
    k8s_audit: dict[str, Any] = {}
    if polaris_json:
        k8s_audit["polaris"] = json.loads(polaris_json.read_text())
    if kube_bench_json:
        k8s_audit["kube_bench"] = json.loads(kube_bench_json.read_text())

    payload: dict[str, Any] = {
        "tenant_id": tenant,
        "scan_kind": "k8s_audit",
        "metadata": {"k8s_audit": k8s_audit},
    }
    if cluster:
        payload["cluster_name"] = cluster

    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{base}/api/v1/scans", json=payload)
        r.raise_for_status()
        scan = r.json()
        scan_id = scan["id"]
        typer.echo(f"Scan {scan_id} ({scan['scan_kind']}) status={scan['status']}")

        done = _wait_scan(client, base, scan_id, wait_timeout)
        typer.echo(f"Final status: {done['status']}")

        fr = client.get(f"{base}/api/v1/findings", params={"scan_id": scan_id, "limit": 500})
        fr.raise_for_status()
        findings = fr.json()

        if output == "json":
            _emit_audit_json(client, base, scan_id, done, findings)
            return

    _print_findings_text(findings)
