"""CloudOpt background worker entrypoint. Processes analysis jobs from Redis queue."""

import os
import sys

# Ensure project root is on path when running as module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from redis import Redis
from rq import Worker

from packages.core.config import get_settings


def main() -> None:
    """Run RQ worker listening on default queue."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker(
        ["default"],
        connection=redis_conn,
    )
    worker.work()


if __name__ == "__main__":
    main()
