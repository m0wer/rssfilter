from os import getenv
import time

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.routers import feed, log, signup, user
from app.constants import ROOT_PATH
from loguru import logger
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from redis import asyncio as aioredis  # type: ignore

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
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
app.include_router(signup.router, prefix="/v1/signup")
app.include_router(user.router, prefix="/v1/user")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(
        f"Processed request in {round(process_time * 1000)} ms. {request.method} {request.url}"
    )
    return response


app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
