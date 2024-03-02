from os import getenv

import requests
from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse
from src.models.user import User

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/api/v1")

router = APIRouter(
    prefix="/feed",
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}/{feed_url:path}")
async def save_feed(user_id, feed_url):
    """Save feed, generate user_id and return filtered feed"""
    user = User(uid=user_id)
    # TODO: Do something with user

    feed = requests.get(feed_url)
    feed_xml = feed.text
    return Response(content=feed_xml, media_type="application/xml")

    # feed = feedparser.parse(feed_url)
    # TODO: Do something with the feed (create article, embeddings...)
    # if feed.status != 200:
    #     return RedirectResponse(feed_url)
    # return feed
    return RedirectResponse(feed_url)
