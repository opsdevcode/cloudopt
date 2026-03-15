"""CloudOpt CLI entrypoint. Run with: cloudopt [command]"""

import typer

from apps.cli.commands import scan

app = typer.Typer(
    name="cloudopt",
    help="CloudOpt — AI-powered FinOps for AWS and Kubernetes.",
    add_completion=False,
)

app.add_typer(scan.scan_app, name="scan")


if __name__ == "__main__":
    app()
