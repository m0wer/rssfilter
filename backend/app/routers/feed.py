import asyncio
from pydantic.networks import HttpUrl
from datetime import datetime, timedelta, timezone
from fastapi import Request
import json
from fastapi import APIRouter, Response, Depends
from sqlmodel import Session, select, or_
from loguru import logger
from app.models.article import Article
from app.models.feed import (
    Feed,
    generate_feed,
    parse_feed,
    UpstreamError,
    SSRFException,
)
from app.models.user import User
from app.recommend import filter_articles
from app.tasks import fetch_feed_batch, enqueue_high_priority
from .common import get_engine
from fastapi import HTTPException
from fastapi import BackgroundTasks

from sqlalchemy.exc import NoResultFound

router = APIRouter(
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


FEED_REFRESH_INTERVAL = timedelta(days=1)  # Adjust as needed


@router.get("/{user_id}/{feed_url:path}")
async def get_feed(
    request: Request,
    user_id: str,
    feed_url: HttpUrl,
    background_tasks: BackgroundTasks,
    engine=Depends(get_engine),
) -> Response:
    with Session(engine, autoflush=False) as session:
        try:
            user: User = session.exec(select(User).where(User.id == user_id)).one()
            user.last_request = datetime.now(timezone.utc)
            if user.is_frozen:
                user.is_frozen = False
                user.frozen_at = None
                logger.info(f"Auto-unfroze user {user_id} due to feed request")
        except NoResultFound:
            logger.info(f"User {user_id} not found in database, creating new user")
            user = User(id=user_id)
            session.add(user)
            session.commit()

        # Feed handling - look up by url or original_url (for redirected feeds)
        try:
            feed: Feed = session.exec(
                select(Feed).where(
                    or_(
                        Feed.url == str(feed_url),
                        Feed.original_url == str(feed_url),
                    )
                )
            ).one()
        except NoResultFound:
            logger.info(
                f"Feed {feed_url} not found in database, fetching from upstream"
            )
            try:
                feed = await parse_feed(feed_url)
            except UpstreamError as e:
                return Response(content=str(e), status_code=502)
            except SSRFException:
                # Don't expose the internal SSRF error details
                raise HTTPException(
                    status_code=403,
                    detail="Access to internal network resources is not allowed",
                )
            session.add(feed)
            try:
                session.commit()
            except Exception as e:
                # might happen if the feed was created before by another thread
                logger.warning(f"Failed to add feed {feed_url} to database: {e}")
                session.rollback()
                feed = session.exec(select(Feed).where(Feed.url == feed.url)).one()
            session.add(feed)
            session.commit()

        if feed not in user.feeds:
            user.feeds.append(feed)
            session.commit()

        # Check if feed needs refreshing
        now = datetime.now(timezone.utc)
        if (
            feed.updated_at is None
            or (now - feed.updated_at.replace(tzinfo=timezone.utc))
            > FEED_REFRESH_INTERVAL
        ):
            logger.info(f"Feed {feed_url} needs refreshing")
            job = enqueue_high_priority(fetch_feed_batch, [feed.id])
            start = datetime.now()
            while job.get_status(refresh=True) != "finished":
                await asyncio.sleep(0.5)
                if (datetime.now() - start) > timedelta(seconds=10):
                    logger.warning(
                        f"Feed {feed_url} refresh job took too long, returning old data"
                    )
                    break
            session.refresh(feed)

        articles = list(
            session.exec(
                select(Article)
                .where(Article.feed_id == feed.id)
                .order_by(Article.pub_date.desc())  # type: ignore[union-attr]
                .limit(30)
            ).all()
        )

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
