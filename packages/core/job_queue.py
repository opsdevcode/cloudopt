"""Enqueue background jobs (RQ) from API or scripts."""

from redis import Redis
from rq import Queue

from packages.core.config import get_settings


def enqueue_dispatch_scan(scan_id: str) -> None:
    """Schedule scan dispatch on the default RQ queue."""
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    Queue("default", connection=conn).enqueue(
        "apps.worker.jobs.dispatch_scan",
        scan_id,
        job_timeout="30m",
    )
