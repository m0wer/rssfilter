import asyncio
import os
import json
from sqlmodel import create_engine, Session, select, update
from datetime import datetime, timezone, timedelta
from loguru import logger
from redis import Redis  # type: ignore
from rq import Queue, Retry

from app.models.article import Article
from app.models.feed import Feed, parse_feed, generate_feed
from app.models.user import User
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


def compute_article_embedding(article_id):
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


def recompute_user_clusters(user_id):
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


def remove_old_embeddings():
    with Session(ENGINE) as session:
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # Perform the update directly in the database
        update_statement = (
            update(Article)
            .where(Article.updated < one_month_ago)
            .where(Article.embedding != None)  # noqa: E711
            .values(embedding=None)
        )

        result = session.exec(update_statement)
        affected_rows = result.rowcount

        session.commit()
        logger.info(f"Removed embeddings from {affected_rows} old articles")


BATCH_SIZE = int(os.getenv("FEED_FETCH_BATCH_SIZE", "10"))


def fetch_feed_batch(feed_ids):
    async def fetch_single_feed(feed):
        try:
            return await parse_feed(feed.url)
        except Exception as e:
            logger.warning(f"Error fetching feed {feed.id}: {e}")
            return None

    async def fetch_multiple_feeds(feeds):
        return await asyncio.gather(*[fetch_single_feed(feed) for feed in feeds])

    with Session(ENGINE) as session:
        feeds = session.exec(select(Feed).where(Feed.id.in_(feed_ids))).all()
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


def compute_embeddings_batch(article_ids):
    with Session(ENGINE) as session:
        articles = session.exec(
            select(Article).where(Article.id.in_(article_ids))
        ).all()
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


def fetch_all_feeds():
    with Session(ENGINE) as session:
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        active_feeds = session.exec(
            select(Feed)
            .join(User.feeds)
            .where(User.last_request > one_month_ago)
            .distinct()
        ).all()

        for i in range(0, len(active_feeds), BATCH_SIZE):
            batch = active_feeds[i : i + BATCH_SIZE]
            enqueue_low_priority(fetch_feed_batch, [feed.id for feed in batch])

    logger.info(
        f"Processed {len(active_feeds)} active feeds in batches of {BATCH_SIZE}"
    )


def log_user_action(user_id: str, article_id: int, link_url: str):
    with Session(ENGINE) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if user is None:
            user = User(id=user_id)
            session.add(user)
        else:
            user.last_request = datetime.now(timezone.utc)
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


def generate_filtered_feed(feed_id: int, user_id: str):
    with Session(ENGINE) as session:
        feed = session.get(Feed, feed_id)
        user = session.get(User, user_id)

        if not feed or not user:
            logger.error(f"Feed {feed_id} or User {user_id} not found")
            return None

        articles = feed.articles[-30:]  # Last 30 articles

        if user.clusters:
            cluster_centers = json.loads(user.clusters)
            filtered_articles = filter_articles(articles, cluster_centers)
        else:
            filtered_articles = articles

        return generate_feed(feed, filtered_articles, user_id)


# Helper functions to enqueue tasks
def enqueue_low_priority(func, *args, **kwargs):
    return low_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=3))


def enqueue_medium_priority(func, *args, **kwargs):
    return medium_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=3))


def enqueue_high_priority(func, *args, **kwargs):
    return high_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=2))


def enqueue_gpu_task(func, *args, **kwargs):
    return gpu_queue.enqueue(func, args=args, kwargs=kwargs, retry=Retry(max=3))
