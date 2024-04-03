from pydantic.networks import HttpUrl
from fastapi import Request
import json
from fastapi import APIRouter, Response, Depends
from sqlmodel import Session, select
from loguru import logger
from app.models.feed import Feed, generate_feed, parse_feed, UpstreamError
from app.models.user import User
from app.recommend import filter_articles
from .common import get_engine

# from fastapi_cache.coder import PickleCoder
# from fastapi_cache.decorator import cache
from sqlalchemy.orm.exc import NoResultFound

router = APIRouter(
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}/{feed_url:path}")
# @cache(expire=300, coder=PickleCoder)
async def get_feed(
    request: Request, user_id: str, feed_url: HttpUrl, engine=Depends(get_engine)
) -> str:
    """Get filtered feed."""
    if request.query_params:
        feed_url = f"{feed_url}?"  # type: ignore
        for key, value in request.query_params.items():
            feed_url = f"{feed_url}&{key}={value}"  # type: ignore
    with Session(engine, autoflush=False) as session:
        try:
            user: User = session.exec(select(User).where(User.id == user_id)).one()
        except NoResultFound:
            logger.info(f"User {user_id} not found in database, creating new user")
            user = User(id=user_id)
            session.add(user)
            try:
                session.commit()
            except Exception as e:
                # might happen if the user was created before by another thread
                logger.warning(f"Failed to add user {user_id} to database: {e}")
                session.rollback()
                user = session.exec(select(User).where(User.id == user_id)).one()

        try:
            feed: Feed = session.exec(
                select(Feed).where(Feed.url == str(feed_url))
            ).one()
        except NoResultFound:
            logger.info(
                f"Feed {feed_url} not found in database, fetching from upstream"
            )
            try:
                feed = await parse_feed(feed_url)
            except UpstreamError as e:
                return Response(content=str(e), status_code=502)
            session.add(feed)
            try:
                session.commit()
            except Exception as e:
                # might happen if the feed was created before by another thread
                logger.warning(f"Failed to add feed {feed_url} to database: {e}")
                session.rollback()
                feed = session.exec(select(Feed).where(Feed.url == str(feed_url))).one()
        if feed not in user.feeds:
            user.feeds.append(feed)
        session.commit()

        articles = feed.articles[-30:]

        if user.clusters:
            filtered_articles = filter_articles(
                articles=articles, cluster_centers=json.loads(user.clusters)
            )
            logger.debug(
                f"Returning {len(filtered_articles)}/{len(articles)} articles for user {user_id}"
            )
        else:
            logger.debug(
                f"No cluster centers found for user {user_id}, returning all articles"
            )
            filtered_articles = articles

        custom_feed = generate_feed(feed, filtered_articles, user_id)

    return Response(content=custom_feed, media_type="application/xml")
