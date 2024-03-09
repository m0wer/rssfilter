from os import getenv
import time

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from sqlmodel import SQLModel
from app.routers.common import get_engine
from app.routers import feed, log
from loguru import logger
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from redis import asyncio as aioredis

from contextlib import asynccontextmanager

ROOT_PATH = getenv("ROOT_PATH", "/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(get_engine())
    if (REDIS_URL := getenv("REDIS_URL")) is not None:
        redis = aioredis.from_url(REDIS_URL)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    else:
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    yield


app = FastAPI(root_path=ROOT_PATH, lifespan=lifespan)

app.include_router(feed.router, prefix="/v1/feed")
app.include_router(log.router, prefix="/v1/log")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.debug(f"Processed request in {process_time:.3f} seconds")
    return response


app.add_middleware(GZipMiddleware, minimum_size=1000)
