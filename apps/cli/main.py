"""CloudOpt CLI entrypoint. Run with: cloudopt [command]"""

import typer

from apps.cli.commands import audit, scan

app = typer.Typer(
    name="cloudopt",
    help="CloudOpt — FinOps, AWS posture, and Kubernetes audits for AWS and Kubernetes.",
    add_completion=False,
)

app.add_typer(scan.scan_app, name="scan")
app.add_typer(audit.audit_app, name="audit")


if __name__ == "__main__":
    app()
