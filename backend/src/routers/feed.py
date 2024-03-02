import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from os import getenv

import requests
from fastapi import APIRouter, Response
from loguru import logger
from sqlmodel import Session, select
from src.db import engine
from src.models.feed import Feed
from src.models.user import User

from sqlmodel import Session, select


from src.db import engine
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
    feed_root = ET.fromstring(feed_response.text)
    namespace = feed_root.tag.split("}")[0][1:]
    for link in feed_root.findall(".//{%s}link" % namespace):
        old_link = link.get("href")
        logger.debug("OLD LINK: {link}", link=old_link)
        new_link = f"{API_BASE_URL}/{ROOT_PATH}/v1/log/{user_id}/{old_link}"
        logger.debug("NEW LINK: {link}", link=new_link)
        link.set("href", new_link)

    modified_feed = ET.tostring(feed_root, encoding="unicode")
    return Response(content=modified_feed, media_type="application/xml")
