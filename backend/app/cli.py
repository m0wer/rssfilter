import asyncio
import typer
from sqlmodel import create_engine
import os
from sqlmodel import Session, SQLModel

from .models.article import Article  # noqa: F401
from .models.feed import Feed, parse_feed  # noqa: F401
from .models.user import User  # noqa: F401
from .recommend import compute_embeddings
from loguru import logger

models = [Article, Feed, User]

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

ENGINE = create_engine(
    DATABASE_URL,
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


if __name__ == "__main__":
    SQLModel.metadata.create_all(ENGINE)
    cli()
