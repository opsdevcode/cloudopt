"""Worker job unit tests (mocked DB and queue)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from apps.worker import jobs


def test_dispatch_scan_unknown_kind_fails() -> None:
    mock_scan = MagicMock()
    mock_scan.scan_kind = "invalid_kind"
    mock_scan.started_at = None

    mock_session = MagicMock()
    mock_session.scalar.return_value = mock_scan

    with patch.object(jobs, "sync_session_scope") as scope:
        scope.return_value.__enter__.return_value = mock_session
        with patch.object(jobs, "_fail_scan") as fail_scan:
            result = jobs.dispatch_scan("scan-123")

    assert result["status"] == "failed"
    fail_scan.assert_called_once()


def test_dispatch_scan_not_found() -> None:
    mock_session = MagicMock()
    mock_session.scalar.return_value = None

    with patch.object(jobs, "sync_session_scope") as scope:
        scope.return_value.__enter__.return_value = mock_session
        result = jobs.dispatch_scan("missing-id")

    assert result["status"] == "error"
    assert result["detail"] == "scan not found"


def test_enqueue_dispatch_scan_uses_rq() -> None:
    mock_queue = MagicMock()
    mock_redis = MagicMock()

    with patch("packages.core.job_queue.Redis.from_url", return_value=mock_redis):
        with patch("packages.core.job_queue.Queue", return_value=mock_queue) as queue_cls:
            from packages.core.job_queue import enqueue_dispatch_scan

            enqueue_dispatch_scan("scan-abc")

    queue_cls.assert_called_once_with("default", connection=mock_redis)
    mock_queue.enqueue.assert_called_once_with(
        "apps.worker.jobs.dispatch_scan",
        "scan-abc",
        job_timeout="30m",
    )
