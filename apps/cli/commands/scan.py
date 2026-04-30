"""cloudopt scan — run cost optimization scan."""


import typer

scan_app = typer.Typer(help="Run a cost optimization scan.")


@scan_app.callback(invoke_without_command=True)
def scan_cmd(
    ctx: typer.Context,
    cluster: str | None = typer.Option(
        None,
        "--cluster",
        "-c",
        help="Kubernetes cluster name to analyze (e.g. production).",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: text (default) or json.",
    ),
) -> None:
    """
    Run a CloudOpt cost optimization scan.

    Analyzes AWS/Kubernetes infrastructure and prints top savings opportunities.
    """
    if ctx.invoked_subcommand is not None:
        return
    _run_scan(cluster=cluster or "default", output=output or "text")


def _run_scan(cluster: str, output: str) -> None:
    """Execute scan and print results. Placeholder: stub output for MVP."""
    # Placeholder: in full implementation this would call API or run analysis locally
    if output == "json":
        typer.echo(
            f'{{"cluster": "{cluster}", "findings": [], "total_savings_monthly": 0}}'
        )
        return

    typer.echo("")
    typer.echo("CloudOpt Scan Results")
    typer.echo("=" * 40)
    typer.echo("")
    typer.echo(f"Cluster: {cluster}")
    typer.echo("")
    typer.echo("Recommendation:")
    typer.echo("  Reduce node size from m6i.2xlarge → m6i.xlarge")
    typer.echo("")
    typer.echo("Savings:")
    typer.echo("  $2,134/month")
    typer.echo("")
    typer.echo("(Run with real AWS/EKS data for full analysis.)")
    typer.echo("")
