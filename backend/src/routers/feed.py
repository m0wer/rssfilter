from datetime import datetime, timezone
from os import getenv

import requests
from fastapi import APIRouter, Response
from sqlmodel import Session, select
from src.db import engine
from src.models.feed import Feed
from src.models.user import User
from src.modules.rss import RSS

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/").rstrip("/")
ROOT_PATH = getenv("ROOT_PATH", "/api").lstrip("/")

router = APIRouter(
    prefix="/feed",
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}/{feed_url:path}")
async def save_feed(user_id, feed_url):
    """Save feed, generate user_id and return filtered feed"""
    with Session(engine) as session:
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()
        if user is None:
            user = User(id=user_id)
            session.add(user)
        else:
            user.last_request = datetime.now(timezone.utc)
        statement = select(Feed).where(Feed.url == feed_url)
        feed = session.exec(statement).first()
        if feed is None:
            feed = Feed(url=feed_url)
            session.add(feed)
        else:
            feed.updated = datetime.now(timezone.utc)
        if feed not in user.feeds:
            user.feeds.append(feed)
        session.commit()

    feed_response = requests.get(feed_url)
    feed = RSS(feed_response.text, user_id)
    modified_feed = feed.get_modified_rss()
    return Response(content=modified_feed, media_type="application/xml")
