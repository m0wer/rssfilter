#!/usr/bin/env python
from sys import argv
from redis import Redis
from rq import Worker

# Preload libraries
import os


w = Worker(
    # get the queue names from the arguments
    argv[1:],
    connection=Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379")),
)
w.work()
