import typer
from sqlmodel import create_engine
import os
from sqlmodel import Session, SQLModel

from .models.article import Article  # noqa: F401
from .models.feed import Feed  # noqa: F401
from .models.user import User  # noqa: F401
from .recommend import compute_embeddings
from loguru import logger

models = [Article, Feed, User]


cli = typer.Typer()


@cli.command()
def compute_missing_embeddings():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    engine = create_engine(
        db_url,
        echo=bool(os.getenv("DEBUG", False)),
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
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


if __name__ == "__main__":
    cli()
