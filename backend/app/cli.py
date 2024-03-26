import asyncio
import time
import json
import typer
from sqlmodel import create_engine, select
import os
from sqlmodel import Session, SQLModel
from datetime import datetime, timezone
from rich.progress import track

from .models.article import Article  # noqa: F401
from .models.feed import Feed, parse_feed  # noqa: F401
from .models.user import User  # noqa: F401
from .recommend import compute_embeddings, cluster_articles
from loguru import logger

models = [Article, Feed, User]

ENGINE = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///data/db.sqlite"),
    echo=bool(os.getenv("DEBUG", False)),
    connect_args={"check_same_thread": False},
)

cli = typer.Typer()


@cli.command()
def compute_missing_embeddings():
    with Session(ENGINE) as session:
        articles = session.query(Article).filter(Article.embedding == None).all()  # noqa: E711
        n_pending: int = sum(1 for a in articles if a.embedding is None)
        logger.info(f"Computing {n_pending} embeddings")
        try:
            compute_embeddings(articles=articles)
        except Exception as e:
            logger.error(e)
        finally:
            session.commit()
            n_pending_after: int = sum(1 for a in articles if a.embedding is None)
            logger.info(f"Computed {n_pending - n_pending_after} embeddings")


@cli.command()
def fetch_feeds():
    with Session(ENGINE, autoflush=False) as session:
        feeds = session.query(Feed).all()
        for feed in feeds:
            logger.info(f"Fetching {feed.url}")
            start = time.time()
            try:
                parsed_feed = asyncio.run(parse_feed(feed.url))
                logger.debug(f"Found {len(parsed_feed.articles)} articles")
                for article in parsed_feed.articles:
                    article.feed = feed
                    session.add(article)
                    try:
                        session.commit()
                        feed.articles.append(article)
                        logger.debug(f"Added {article.title}")
                    except Exception:
                        logger.debug(f"Article {article.title} already exists")
                        session.rollback()
            except Exception as e:
                logger.error(e)
            finally:
                session.commit()
            logger.info(f"Elapsed time: {time.time() - start:.2f}s")


@cli.command()
def clusters():
    """Compute clusters for all users."""
    with Session(ENGINE) as session:
        users = session.exec(select(User)).all()
        for user in track(users, description="Computing clusters..."):
            if len(user.articles) < 10:
                logger.debug(f"User {user.id} has less than 10 articles, skipping.")
                continue
            logger.info(
                f"Computing clusters for {user.id}, {len(user.articles)} articles"
            )
            start = time.time()
            try:
                cluster_centers = cluster_articles(user.articles).cluster_centers_
                user.clusters = json.dumps(cluster_centers.tolist())
                user.clusters_updated_at = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(e)
            finally:
                session.commit()
            logger.info(f"Elapsed time: {time.time() - start:.2f}s")


if __name__ == "__main__":
    SQLModel.metadata.create_all(ENGINE)
    cli()
