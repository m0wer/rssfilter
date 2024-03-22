from datetime import datetime, timezone

from pydantic.networks import HttpUrl
from fastapi import APIRouter, Response, Depends
from sqlmodel import Session, select
from app.models.feed import Feed, generate_feed, parse_feed, UpstreamError
from app.models.user import User
from .common import get_engine
from fastapi_cache.coder import PickleCoder
from fastapi_cache.decorator import cache
from sqlalchemy.orm.exc import NoResultFound

router = APIRouter(
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


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
