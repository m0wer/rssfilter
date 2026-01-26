import typer
from sqlmodel import create_engine, SQLModel
import os
from app.tasks import (
    fetch_all_feeds,
    remove_old_embeddings,
    freeze_dormant_users,
    cleanup_old_articles,
    cleanup_orphan_user_article_links,
    cleanup_orphan_user_feed_links,
    cleanup_inactive_users,
    vacuum_database,
    get_database_stats,
    run_full_maintenance,
    unfreeze_user,
)
from app.models.article import Article
from app.models.feed import Feed
from app.models.user import User

models = [Article, Feed, User]

ENGINE = create_engine(
    os.getenv("DATABASE_URL", "sqlite:///data/db.sqlite"),
    echo=bool(os.getenv("DEBUG", False)),
    connect_args={"check_same_thread": False},
)

cli = typer.Typer(help="RSS Filter maintenance CLI")


@cli.command()
def fetch_feeds() -> None:
    """Fetch all feeds for active (non-frozen) users."""
    fetch_all_feeds()
    typer.echo("Feed fetch tasks enqueued")


@cli.command()
def clean_embeddings() -> None:
    """Remove embeddings from old articles to save space."""
    count = remove_old_embeddings()
    typer.echo(f"Removed embeddings from {count} articles")


@cli.command()
def freeze_users(days: int = 90) -> None:
    """Freeze users who have been inactive for specified days."""
    os.environ["DORMANT_THRESHOLD_DAYS"] = str(days)
    count = freeze_dormant_users()
    typer.echo(f"Froze {count} dormant users (inactive >{days} days)")


@cli.command()
def unfreeze(user_id: str) -> None:
    """Manually unfreeze a specific user."""
    if unfreeze_user(user_id):
        typer.echo(f"User {user_id} unfrozen successfully")
    else:
        typer.echo(f"User {user_id} was not frozen or does not exist")


@cli.command()
def clean_articles(days: int = 180) -> None:
    """Delete old unread articles to free up space."""
    count = cleanup_old_articles(days)
    typer.echo(f"Deleted {count} old unread articles (>{days} days)")


@cli.command()
def clean_orphans() -> None:
    """Remove orphan user-article and user-feed links."""
    article_links = cleanup_orphan_user_article_links()
    feed_links = cleanup_orphan_user_feed_links()
    typer.echo(
        f"Deleted {article_links} orphan article links, {feed_links} orphan feed links"
    )


@cli.command()
def clean_users(days: int = 365) -> None:
    """Delete inactive users with no feeds or articles."""
    count = cleanup_inactive_users(days)
    typer.echo(f"Deleted {count} inactive users (>{days} days, no feeds/articles)")


@cli.command()
def vacuum() -> None:
    """Run VACUUM and ANALYZE on the database."""
    vacuum_database()
    typer.echo("Database vacuumed and analyzed")


@cli.command()
def stats() -> None:
    """Show database statistics."""
    stats = get_database_stats()
    typer.echo("\nDatabase Statistics:")
    typer.echo("-" * 40)
    typer.echo(f"Users: {stats['users']['total']}")
    typer.echo(f"  - Active (30d): {stats['users']['active_30d']}")
    typer.echo(f"  - Frozen: {stats['users']['frozen']}")
    typer.echo(f"Feeds: {stats['feeds']['total']}")
    typer.echo(f"Articles: {stats['articles']['total']}")
    typer.echo(f"  - With embeddings: {stats['articles']['with_embeddings']}")
    typer.echo(f"User-Article Links: {stats['links']['user_article']}")
    typer.echo(f"User-Feed Links: {stats['links']['user_feed']}")


@cli.command()
def maintenance() -> None:
    """Run full maintenance cycle (freeze, clean, vacuum)."""
    typer.echo("Starting full maintenance cycle...")
    results = run_full_maintenance()
    typer.echo("\nMaintenance Results:")
    typer.echo("-" * 40)
    typer.echo(f"Frozen users: {results['frozen_users']}")
    typer.echo(f"Removed embeddings: {results['removed_embeddings']}")
    typer.echo(f"Deleted articles: {results['deleted_articles']}")
    typer.echo(f"Orphan article links: {results['orphan_article_links']}")
    typer.echo(f"Orphan feed links: {results['orphan_feed_links']}")
    typer.echo("Database vacuumed: Yes")


if __name__ == "__main__":
    SQLModel.metadata.create_all(ENGINE)
    cli()
