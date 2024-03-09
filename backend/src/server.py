from os import getenv
import time

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from sqlmodel import SQLModel
from src.routers.common import get_engine
from src.routers import feed, log
from loguru import logger

from contextlib import asynccontextmanager

ROOT_PATH = getenv("ROOT_PATH", "/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(get_engine())
    yield


app = FastAPI(root_path=ROOT_PATH, lifespan=lifespan)

app.include_router(feed.router)
app.include_router(feed.router, prefix="/v1")
app.include_router(log.router, prefix="/v1")
app.include_router(feed.router, prefix="/latest")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.debug(f"Processed request in {process_time:.3f} seconds")
    return response


app.add_middleware(GZipMiddleware, minimum_size=1000)
