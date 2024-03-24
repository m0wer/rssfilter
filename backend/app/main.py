from os import getenv
import time

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from sqlmodel import SQLModel
from app.routers.common import get_engine
from app.routers import feed, log
from app.constants import ROOT_PATH
from loguru import logger
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from redis import asyncio as aioredis  # type: ignore

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(get_engine())
    if (REDIS_URL := getenv("REDIS_URL")) is not None:
        redis = aioredis.from_url(REDIS_URL)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    else:
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    yield


app = FastAPI(root_path=f"/{ROOT_PATH}" if ROOT_PATH else "", lifespan=lifespan)
logger.debug(f"Root path: {app.root_path}")

app.include_router(feed.router, prefix="/v1/feed")
app.include_router(log.router, prefix="/v1/log")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(
        f"Processed request in {round(process_time*1000)} ms. {request.method} {request.url}"
    )
    return response


app.add_middleware(GZipMiddleware, minimum_size=1000)
