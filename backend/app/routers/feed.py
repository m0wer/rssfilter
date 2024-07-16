import asyncio
from pydantic.networks import HttpUrl
import re
import time
from fastapi import APIRouter, Response, Depends, HTTPException
from sqlmodel import Session, select
from app.models.feed import Feed
from app.models.user import User
from app.tasks import (
    enqueue_high_priority,
    generate_filtered_feed,
    fetch_feed,
    enqueue_medium_priority,
)
from .common import get_engine

router = APIRouter(
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}/{feed_url:path}")
async def get_feed(
    user_id: str, feed_url: HttpUrl, engine=Depends(get_engine)
) -> Response:
    """Get filtered feed."""
    if feed_url.host and re.match(
        r"^(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b", feed_url.host
    ):
        raise HTTPException(status_code=422, detail="Invalid URL")

    with Session(engine, autoflush=False) as session:
        feed = session.exec(select(Feed).where(Feed.url == str(feed_url))).first()
        if not feed:
            # If feed does not exist, create it and fetch the articles
            feed = Feed(url=str(feed_url))
            session.add(feed)
            session.commit()
            job = enqueue_medium_priority(fetch_feed, feed.id)
            while not job.result:
                await asyncio.sleep(0.5)

        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            user = User(id=user_id)
            session.add(user)
            session.commit()

        if feed not in user.feeds:
            user.feeds.append(feed)
            session.commit()

    # Enqueue the task to generate the filtered feed
    job = enqueue_high_priority(generate_filtered_feed, feed.id, user_id)

    # Wait for the job to complete (with a timeout)
    timeout = 30  # 30 seconds timeout
    result = job.result
    start_time = time.time()
    while result is None:
        if time.time() - start_time > timeout:
            raise HTTPException(status_code=504, detail="Feed generation timed out")
        await asyncio.sleep(0.05)
        result = job.result

    if result is None:
        raise HTTPException(status_code=504, detail="Feed generation failed")

    return Response(content=result, media_type="application/xml")
