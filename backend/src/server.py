from os import getenv

from fastapi import FastAPI
from sqlmodel import SQLModel
from src.db import engine
from src.routers import feed, log

ROOT_PATH = getenv("ROOT_PATH", "/")


def create_app():
    app = FastAPI(root_path=ROOT_PATH)

    app.include_router(feed.router)
    app.include_router(feed.router, prefix="/v1")
    app.include_router(log.router, prefix="/v1")
    app.include_router(feed.router, prefix="/latest")

    return app


app = create_app()


# on startup, setup sqlmodel
@app.on_event("startup")
async def startup():
    SQLModel.metadata.create_all(engine)
