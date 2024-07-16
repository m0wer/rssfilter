import typer
from sqlmodel import create_engine, SQLModel
import os
from app.tasks import fetch_all_feeds, remove_old_embeddings
from app.models.article import Article
from app.models.feed import Feed
from app.models.user import User

models = [Article, Feed, User]

ENGINE = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///data/db.sqlite"),
    echo=bool(os.getenv("DEBUG", False)),
    connect_args={"check_same_thread": False},
)

cli = typer.Typer()


@cli.command()
def fetch_feeds():
    """Enqueue task to fetch all feeds."""
    fetch_all_feeds()


@cli.command()
def clean_embeddings():
    """Enqueue task to remove old embeddings."""
    remove_old_embeddings()


if __name__ == "__main__":
    SQLModel.metadata.create_all(ENGINE)
    cli()
