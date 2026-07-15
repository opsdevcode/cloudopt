"""CLI smoke tests (no network or AWS calls)."""

from __future__ import annotations

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


def test_cloudopt_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "CloudOpt" in result.stdout


def test_scan_help() -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "cost optimization scan" in result.stdout.lower()


def test_audit_help() -> None:
    result = runner.invoke(app, ["audit", "--help"])
    assert result.exit_code == 0
    assert "posture" in result.stdout.lower()


def test_scan_stub_output() -> None:
    """Default scan command prints placeholder output without calling AWS."""
    result = runner.invoke(app, ["scan", "--cluster", "test-cluster"])
    assert result.exit_code == 0
    assert "test-cluster" in result.stdout or "cluster" in result.stdout.lower()


def test_unknown_command_fails() -> None:
    result = runner.invoke(app, ["not-a-command"])
    assert result.exit_code != 0
