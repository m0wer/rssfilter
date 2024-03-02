from fastapi import FastAPI
from sqlmodel import SQLModel

from src.routers import feed, log
from src.db import engine

def create_app():
    app = FastAPI()

    app.include_router(feed.router)
    app.include_router(feed.router, prefix="/api/v1")
    app.include_router(log.router, prefix="/api/v1")
    app.include_router(feed.router, prefix="/api/latest")

    return app


app = create_app()

# on startup, setup sqlmodel
@app.on_event("startup")
async def startup():
    SQLModel.metadata.create_all(engine)
