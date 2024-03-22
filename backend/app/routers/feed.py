from datetime import datetime, timezone

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from pydantic.networks import HttpUrl
from fastapi import APIRouter, Response, Depends
from sqlmodel import Session, select
from app.models.feed import Feed, generate_feed
from app.models.user import User
from app.models.article import Article
from .common import get_engine
from fastapi_cache.coder import PickleCoder
from fastapi_cache.decorator import cache
import feedparser
from sqlalchemy.orm.exc import NoResultFound
from dateutil import parser

router = APIRouter(
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


class UpstreamError(Exception):
    pass


async def parse_feed(feed_url: HttpUrl) -> Feed:
    """Register a new feed."""
    async with ClientSession() as aiohttp_session:
        try:
            async with aiohttp_session.get(
                str(feed_url), headers={"User-agent": "Mozilla/5.0"}
            ) as response:
                response.raise_for_status()
                feed_response = await response.text()
        except ClientError as e:
            raise UpstreamError(f"Error fetching feed: {e}") from e
    parsed = feedparser.parse(feed_response)
    feed = Feed(
        url=str(feed_url),
        title=parsed.feed.get("title"),
        description=parsed.feed.get("description"),
        logo=parsed.feed.get("logo"),
        language=parsed.feed.get("language"),
        articles=[
            Article(
                title=entry.title,
                url=entry.link,
                description=entry.description,
                comments_url=entry.get("comments"),
                pub_date=parser.parse(entry.published),
            )
            for entry in parsed.entries
        ],
    )
    return feed


@router.get("/{user_id}/{feed_url:path}")
@cache(expire=300, coder=PickleCoder)
async def get_feed(user_id: str, feed_url: HttpUrl, engine=Depends(get_engine)) -> str:
    """Get filtered feed."""
    with Session(engine, autoflush=False) as session:
        try:
            user: User = session.exec(select(User).where(User.id == user_id)).one()
        except NoResultFound:
            user = User(id=user_id)
            session.add(user)
        else:
            user.last_request = datetime.now(timezone.utc)
        try:
            feed: Feed = session.exec(
                select(Feed).where(Feed.url == str(feed_url))
            ).one()
        except NoResultFound:
            try:
                feed = await parse_feed(feed_url)
            except UpstreamError as e:
                return Response(content=str(e), status_code=502)
            session.add(feed)
        if feed not in user.feeds:
            user.feeds.append(feed)
        session.commit()

        # select the last 20 articles
        articles = feed.articles[-20:]

        custom_feed = generate_feed(feed, articles, user_id)

    return Response(content=custom_feed, media_type="application/xml")
