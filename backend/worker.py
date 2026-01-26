#!/usr/bin/env python
from sys import argv
from redis import Redis  # type: ignore
from rq import Worker

# Preload libraries
import os
from loguru import logger


queue_names: list[str] = argv[1:]
logger.info(f"Starting worker with queues: {queue_names}")

w = Worker(
    queue_names,
    connection=Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379")),
)
w.work()
