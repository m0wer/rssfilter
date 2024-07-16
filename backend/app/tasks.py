import asyncio
import os
import json
from sqlmodel import create_engine, Session, select
from datetime import datetime, timezone, timedelta
from loguru import logger
from redis import Redis
from rq import Queue

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
low_queue = Queue("low", connection=redis_conn)
medium_queue = Queue("medium", connection=redis_conn)
high_queue = Queue("high", connection=redis_conn)
gpu_queue = Queue("gpu", connection=redis_conn)


def fetch_feed(feed_id):
    with Session(ENGINE) as session:
        feed = session.get(Feed, feed_id)
        if not feed:
            logger.error(f"Feed {feed_id} not found")
            return

        try:
            parsed_feed = asyncio.run(parse_feed(feed.url))
            for article in parsed_feed.articles:
                existing_article = session.exec(
                    select(Article).where(Article.url == article.url)
                ).first()
                if not existing_article:
                    article.feed = feed
                    session.add(article)
                    session.commit()
                    gpu_queue.enqueue(compute_article_embedding, article.id)

            logger.info(
                f"Fetched {len(parsed_feed.articles)} articles for feed {feed_id}"
            )
        except Exception as e:
            logger.error(f"Error fetching feed {feed_id}: {e}")


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
        old_articles = session.exec(
            select(Article)
            .where(Article.updated < one_month_ago)
            .where(Article.embedding is not None)
        ).all()

        for article in old_articles:
            article.embedding = None

        session.commit()
        logger.info(f"Removed embeddings from {len(old_articles)} old articles")


def fetch_all_feeds():
    with Session(ENGINE) as session:
        feeds = session.exec(select(Feed)).all()
        for feed in feeds:
            low_queue.enqueue(fetch_feed, feed.id)
    logger.info(f"Enqueued fetch tasks for {len(feeds)} feeds")


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
            medium_queue.enqueue(recompute_user_clusters, user.id)

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
    return low_queue.enqueue(func, *args, **kwargs)


def enqueue_medium_priority(func, *args, **kwargs):
    return medium_queue.enqueue(func, *args, **kwargs)


def enqueue_high_priority(func, *args, **kwargs):
    return high_queue.enqueue(func, *args, **kwargs)
