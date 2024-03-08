from os import getenv

from fastapi import FastAPI
from sqlmodel import SQLModel
from src.routers.common import get_engine
from src.routers import feed, log

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
