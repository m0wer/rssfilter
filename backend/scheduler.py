#!/usr/bin/env python
"""RQ Scheduler for periodic tasks.

This script sets up recurring jobs using RQ's native scheduler functionality.
It runs as a separate process and enqueues jobs at specified intervals.

Scheduled tasks:
- fetch_all_feeds: Every hour - fetches all active feeds
- run_full_maintenance: Daily at 4am UTC - cleanup and optimization
- retry_disabled_feeds: Weekly on Sunday at 3am UTC - retry failed feeds
"""

import os
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypedDict

from croniter import croniter  # type: ignore[import-untyped]
from loguru import logger
from redis import Redis  # type: ignore[attr-defined]
from rq import Queue

from app.tasks import (
    fetch_all_feeds,
    run_full_maintenance,
    retry_disabled_feeds,
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(REDIS_URL)

# Use the low queue for scheduled tasks (they're not urgent)
scheduler_queue = Queue("low", connection=redis_conn)


class ScheduledTask(TypedDict):
    """Type definition for scheduled task configuration."""

    func: Callable[[], Any]
    job_id: str
    cron: str
    description: str


def run_scheduler() -> None:
    """Main scheduler loop using RQ's built-in scheduler."""
    from time import sleep

    logger.info("Starting RQ scheduler")

    # Define scheduled tasks with cron expressions
    tasks: list[ScheduledTask] = [
        ScheduledTask(
            func=fetch_all_feeds,
            job_id="scheduled:fetch_all_feeds",
            cron="0 * * * *",  # Every hour at minute 0
            description="Fetch all active feeds",
        ),
        ScheduledTask(
            func=run_full_maintenance,
            job_id="scheduled:run_full_maintenance",
            cron="0 4 * * *",  # Daily at 4am UTC
            description="Run full maintenance (cleanup, vacuum)",
        ),
        ScheduledTask(
            func=retry_disabled_feeds,
            job_id="scheduled:retry_disabled_feeds",
            cron="0 3 * * 0",  # Weekly on Sunday at 3am UTC
            description="Retry disabled feeds",
        ),
    ]

    # Track next run times
    next_runs: dict[str, datetime] = {}
    for task in tasks:
        cron = croniter(task["cron"], datetime.now(timezone.utc))
        next_runs[task["job_id"]] = cron.get_next(datetime)
        logger.info(
            f"Task '{task['job_id']}' next run: {next_runs[task['job_id']].isoformat()}"
        )

    while True:
        now = datetime.now(timezone.utc)

        for task in tasks:
            job_id = task["job_id"]
            if now >= next_runs[job_id]:
                logger.info(f"Running scheduled task: {task['description']}")
                try:
                    scheduler_queue.enqueue(  # type: ignore[arg-type]
                        task["func"],
                        job_id=f"{job_id}:{now.strftime('%Y%m%d%H%M')}",
                        job_timeout=600,  # 10 minute timeout for scheduled jobs
                    )
                except Exception as e:
                    logger.error(f"Failed to enqueue {job_id}: {e}")

                # Calculate next run
                cron = croniter(task["cron"], now)
                next_runs[job_id] = cron.get_next(datetime)
                logger.info(
                    f"Task '{job_id}' next run: {next_runs[job_id].isoformat()}"
                )

        # Sleep for 60 seconds before checking again
        sleep(60)


if __name__ == "__main__":
    run_scheduler()
