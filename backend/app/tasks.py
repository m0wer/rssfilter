import asyncio
import os
import json
from sqlmodel import create_engine, Session, select, update, delete, text
from sqlalchemy import func
from sqlalchemy.engine import Connection
from datetime import datetime, timezone, timedelta
from loguru import logger
from redis import Redis  # type: ignore
from rq import Queue, Retry
from pydantic.networks import HttpUrl

from app.models.article import Article
from app.models.feed import (
    Feed,
    parse_feed,
    generate_feed,
    SSRFException,
    UpstreamError,
)
from app.models.user import User
from app.models.relations import UserArticleLink, UserFeedLink
from app.recommend import compute_embeddings, cluster_articles, filter_articles

ENGINE = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///data/db.sqlite"),
    echo=bool(os.getenv("DEBUG", False)),
    connect_args={"check_same_thread": False},
)

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
low_queue = Queue("low", connection=redis_conn, default_timeout=60)
medium_queue = Queue("medium", connection=redis_conn, default_timeout=60)
high_queue = Queue("high", connection=redis_conn, default_timeout=20)
gpu_queue = Queue("gpu", connection=redis_conn, default_timeout=300)

DORMANT_THRESHOLD_DAYS = int(os.getenv("DORMANT_THRESHOLD_DAYS", "90"))
ARTICLE_RETENTION_DAYS = int(os.getenv("ARTICLE_RETENTION_DAYS", "180"))
EMBEDDING_RETENTION_DAYS = int(os.getenv("EMBEDDING_RETENTION_DAYS", "30"))


def compute_article_embedding(article_id: int) -> None:
    with Session(ENGINE) as session:
        article = session.get(Article, article_id)
        if not article or article.embedding:
            return

        try:
            compute_embeddings([article])
            session.commit()
            logger.info(f"Computed embedding for article {article_id}")
        except Exception as e:
            logger.error(f"Error computing embedding for article {article_id}: {e}")


def recompute_user_clusters(user_id: str) -> None:
    with Session(ENGINE) as session:
        user = session.get(User, user_id)
        if not user or len(user.articles) < 10:
            return

        try:
            cluster_centers = cluster_articles(user.articles).cluster_centers_
            user.clusters = json.dumps(cluster_centers.tolist())
            user.clusters_updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Recomputed clusters for user {user_id}")
        except Exception as e:
            logger.error(f"Error recomputing clusters for user {user_id}: {e}")


def remove_old_embeddings() -> int:
    with Session(ENGINE) as session:
        threshold = datetime.now(timezone.utc) - timedelta(
            days=EMBEDDING_RETENTION_DAYS
        )

        update_statement = (
            update(Article)
            .where(Article.updated < threshold)  # type: ignore[arg-type]
            .where(Article.embedding.isnot(None))  # type: ignore[union-attr]
            .values(embedding=None)
        )

        result = session.exec(update_statement)  # type: ignore[call-overload]
        affected_rows = result.rowcount

        session.commit()
        logger.info(f"Removed embeddings from {affected_rows} old articles")
        return affected_rows


def freeze_dormant_users() -> int:
    with Session(ENGINE) as session:
        threshold = datetime.now(timezone.utc) - timedelta(days=DORMANT_THRESHOLD_DAYS)
        now = datetime.now(timezone.utc)

        update_statement = (
            update(User)
            .where(User.last_request < threshold)  # type: ignore[arg-type]
            .where(User.is_frozen.is_(False))  # type: ignore[attr-defined]
            .values(is_frozen=True, frozen_at=now)
        )

        result = session.exec(update_statement)  # type: ignore[call-overload]
        affected_rows = result.rowcount

        session.commit()
        logger.info(
            f"Froze {affected_rows} dormant users (inactive >{DORMANT_THRESHOLD_DAYS} days)"
        )
        return affected_rows


def unfreeze_user(user_id: str) -> bool:
    with Session(ENGINE) as session:
        user = session.get(User, user_id)
        if user and user.is_frozen:
            user.is_frozen = False
            user.frozen_at = None
            user.last_request = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Unfroze user {user_id}")
            return True
        return False


def cleanup_old_articles(retention_days: int | None = None) -> int:
    if retention_days is None:
        retention_days = ARTICLE_RETENTION_DAYS

    with Session(ENGINE) as session:
        threshold = datetime.now(timezone.utc) - timedelta(days=retention_days)

        read_article_ids = select(UserArticleLink.article_id).distinct()

        delete_statement = (
            delete(Article)
            .where(Article.updated < threshold)  # type: ignore[arg-type]
            .where(Article.id.notin_(read_article_ids))  # type: ignore[union-attr]
        )

        result = session.exec(delete_statement)  # type: ignore[call-overload]
        deleted_count = result.rowcount

        session.commit()
        logger.info(
            f"Deleted {deleted_count} old articles (>{retention_days} days, unread)"
        )
        return deleted_count


def cleanup_orphan_user_article_links() -> int:
    with Session(ENGINE) as session:
        existing_article_ids = select(Article.id)

        delete_statement = delete(UserArticleLink).where(
            UserArticleLink.article_id.notin_(existing_article_ids)  # type: ignore[union-attr]
        )

        result = session.exec(delete_statement)  # type: ignore[call-overload]
        deleted_count = result.rowcount

        session.commit()
        logger.info(f"Deleted {deleted_count} orphan user-article links")
        return deleted_count


def cleanup_orphan_user_feed_links() -> int:
    with Session(ENGINE) as session:
        existing_feed_ids = select(Feed.id)

        delete_statement = delete(UserFeedLink).where(
            UserFeedLink.feed_id.notin_(existing_feed_ids)  # type: ignore[union-attr]
        )

        result = session.exec(delete_statement)  # type: ignore[call-overload]
        deleted_count = result.rowcount

        session.commit()
        logger.info(f"Deleted {deleted_count} orphan user-feed links")
        return deleted_count


def cleanup_inactive_users(inactive_days: int = 365) -> int:
    with Session(ENGINE) as session:
        threshold = datetime.now(timezone.utc) - timedelta(days=inactive_days)

        inactive_user_ids = (
            select(User.id)
            .where(User.last_request < threshold)  # type: ignore[arg-type]
            .where(
                ~User.id.in_(  # type: ignore[attr-defined]
                    select(UserArticleLink.user_id).distinct()
                )
            )
            .where(
                ~User.id.in_(  # type: ignore[attr-defined]
                    select(UserFeedLink.user_id).distinct()
                )
            )
        )

        delete_statement = delete(User).where(
            User.id.in_(inactive_user_ids)  # type: ignore[attr-defined]
        )

        result = session.exec(delete_statement)  # type: ignore[call-overload]
        deleted_count = result.rowcount

        session.commit()
        logger.info(
            f"Deleted {deleted_count} inactive users (>{inactive_days} days, no feeds/articles)"
        )
        return deleted_count


def vacuum_database() -> None:
    connection: Connection = ENGINE.connect()
    connection.execute(text("VACUUM"))
    connection.execute(text("ANALYZE"))
    connection.close()
    logger.info("Database vacuumed and analyzed")


def get_database_stats() -> dict:
    with Session(ENGINE) as session:
        stats = {
            "users": {
                "total": session.exec(select(func.count()).select_from(User)).one(),
                "active_30d": session.exec(
                    select(func.count())
                    .select_from(User)
                    .where(
                        User.last_request
                        > datetime.now(timezone.utc) - timedelta(days=30)
                    )
                ).one(),
                "frozen": session.exec(
                    select(func.count())
                    .select_from(User)
                    .where(User.is_frozen.is_(True))  # type: ignore[attr-defined]
                ).one(),
            },
            "feeds": {
                "total": session.exec(select(func.count()).select_from(Feed)).one(),
            },
            "articles": {
                "total": session.exec(select(func.count()).select_from(Article)).one(),
                "with_embeddings": session.exec(
                    select(func.count())
                    .select_from(Article)
                    .where(Article.embedding.isnot(None))  # type: ignore[union-attr]
                ).one(),
            },
            "links": {
                "user_article": session.exec(
                    select(func.count()).select_from(UserArticleLink)
                ).one(),
                "user_feed": session.exec(
                    select(func.count()).select_from(UserFeedLink)
                ).one(),
            },
        }
        return stats


def run_full_maintenance() -> dict:
    results: dict = {}

    logger.info("Starting full maintenance cycle")

    results["frozen_users"] = freeze_dormant_users()
    results["removed_embeddings"] = remove_old_embeddings()
    results["deleted_articles"] = cleanup_old_articles()
    results["orphan_article_links"] = cleanup_orphan_user_article_links()
    results["orphan_feed_links"] = cleanup_orphan_user_feed_links()

    vacuum_database()
    results["vacuumed"] = True

    logger.info(f"Full maintenance completed: {results}")
    return results


BATCH_SIZE = int(os.getenv("FEED_FETCH_BATCH_SIZE", "10"))


def fetch_feed_batch(feed_ids: list[int]) -> None:
    async def fetch_single_feed(feed: Feed) -> Feed | None:
        try:
            return await parse_feed(HttpUrl(feed.url))
        except (SSRFException, UpstreamError) as e:
            logger.warning(f"Error fetching feed {feed.id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unhandled error fetching feed {feed.id}: {e}")
            return None

    async def fetch_multiple_feeds(feeds: list[Feed]) -> list[Feed | None]:
        return await asyncio.gather(*[fetch_single_feed(feed) for feed in feeds])

    with Session(ENGINE) as session:
        feeds = list(
            session.exec(
                select(Feed).where(Feed.id.in_(feed_ids))  # type: ignore[union-attr]
            ).all()
        )
        results = asyncio.run(fetch_multiple_feeds(feeds))

        new_articles = []
        for feed, parsed_feed in zip(feeds, results):
            feed.updated_at = datetime.now(timezone.utc)

            if parsed_feed is None:
                continue

            for article in parsed_feed.articles:
                existing_article = session.exec(
                    select(Article)
                    .where(Article.feed_id == feed.id)
                    .where(Article.url == article.url)
                ).first()
                if not existing_article:
                    article.feed = feed
                    session.add(article)
                    new_articles.append(article)

        session.commit()

        if new_articles:
            new_article_ids = [article.id for article in new_articles]
            enqueue_gpu_task(compute_embeddings_batch, new_article_ids)

        logger.info(
            f"Fetched {len(feeds)} feeds, added {len(new_articles)} new articles"
        )


def compute_embeddings_batch(article_ids: list[int]) -> None:
    with Session(ENGINE) as session:
        articles = list(
            session.exec(
                select(Article).where(Article.id.in_(article_ids))  # type: ignore[union-attr]
            ).all()
        )
        articles_to_embed = [
            article for article in articles if article.embedding is None
        ]

        if not articles_to_embed:
            return

        try:
            compute_embeddings(articles_to_embed)
            session.commit()
            logger.info(f"Computed embeddings for {len(articles_to_embed)} articles")
        except Exception as e:
            logger.error(f"Error computing embeddings for articles: {e}")


def fetch_all_feeds() -> None:
    with Session(ENGINE) as session:
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        active_feeds = list(
            session.exec(
                select(Feed)
                .join(UserFeedLink, Feed.id == UserFeedLink.feed_id)  # type: ignore[arg-type]
                .join(User, UserFeedLink.user_id == User.id)  # type: ignore[arg-type]
                .where(User.last_request > one_month_ago)
                .where(User.is_frozen.is_(False))  # type: ignore[attr-defined]
                .distinct()
            ).all()
        )

        for i in range(0, len(active_feeds), BATCH_SIZE):
            batch = active_feeds[i : i + BATCH_SIZE]
            enqueue_low_priority(fetch_feed_batch, [feed.id for feed in batch])

    logger.info(
        f"Processed {len(active_feeds)} active feeds in batches of {BATCH_SIZE}"
    )


def log_user_action(user_id: str, article_id: int, link_url: str) -> None:
    with Session(ENGINE) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user is None:
            user = User(id=user_id)
            session.add(user)
        else:
            user.last_request = datetime.now(timezone.utc)
            if user.is_frozen:
                user.is_frozen = False
                user.frozen_at = None
                logger.info(f"Auto-unfroze user {user_id} due to activity")

        article = session.exec(select(Article).where(Article.id == article_id)).first()
        if article is None:
            logger.warning(f"Article {article_id} not found")
            return
        article.updated = datetime.now(timezone.utc)
        session.add(article)

        if article not in user.articles:
            user.articles.append(article)
            session.add(user)
            enqueue_medium_priority(recompute_user_clusters, user.id)

        session.commit()
    logger.info(f"Logged action for user {user_id}, article {article_id}")


def generate_filtered_feed(feed_id: int, user_id: str) -> str | None:
    with Session(ENGINE) as session:
        feed = session.get(Feed, feed_id)
        user = session.get(User, user_id)

        if not feed or not user:
            logger.error(f"Feed {feed_id} or User {user_id} not found")
            return None

        articles = feed.articles[-30:]

        if user.clusters:
            cluster_centers = json.loads(user.clusters)
            filtered_articles = filter_articles(articles, cluster_centers)
        else:
            filtered_articles = articles

        return generate_feed(feed, filtered_articles, user_id)


def enqueue_low_priority(func, *args, **kwargs):  # type: ignore[no-untyped-def]
    return low_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=3))


def enqueue_medium_priority(func, *args, **kwargs):  # type: ignore[no-untyped-def]
    return medium_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=3))


def enqueue_high_priority(func, *args, **kwargs):  # type: ignore[no-untyped-def]
    return high_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=2))


def enqueue_gpu_task(func, *args, **kwargs):  # type: ignore[no-untyped-def]
    return gpu_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=3))
