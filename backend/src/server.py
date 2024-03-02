from fastapi import FastAPI
from routers import feed


def create_app():
    app = FastAPI()

    app.include_router(feed.router)
    app.include_router(feed.router, prefix="/api/v1")
    app.include_router(feed.router, prefix="/api/latest")

    return app


app = create_app()
