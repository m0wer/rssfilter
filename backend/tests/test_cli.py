import pytest
from os import getenv
import json
from typer.testing import CliRunner
from sqlmodel import Session, create_engine, select
from app.models.article import Article
from app.models.feed import Feed
from app.models.user import User
from app.recommend import compute_embeddings
from unittest import mock
from app.cli import cli
from app.cli import SQLModel


runner = CliRunner()


# @pytest.fixture()
# def cli_engine():
#    with mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:////tmp/test.db"}):
#        from app.cli import cli as app_cli
#        from app.cli import ENGINE, SQLModel
#
#        SQLModel.metadata.create_all(ENGINE)
#
#        yield app_cli, ENGINE


@pytest.fixture
def engine(tmpdir):
    """Create a tmp dir and mock the cli.ENGINE with a engine using a file in it."""
    with mock.patch(
        "app.cli.ENGINE",
        create_engine(
            f"sqlite:///{tmpdir}/test.db",
            echo=True,
            connect_args={"check_same_thread": False},
        ),
    ) as engine:
        SQLModel.metadata.create_all(engine)
        yield engine


class TestClusters:
    @pytest.mark.skipif(
        getenv("REDIS_URL") is None, reason="REDIS_URL environment variable not set"
    )
    def test_clusters(self, engine):
        with Session(engine) as session:
            feed = Feed(
                url="https://example.com/feed.xml",
                title="Test feed",
                description="Test feed",
            )
            articles = [
                Article(
                    title=f"Article {i}",
                    description=f"Dummy article number {i}",
                    url=f"https://example.com/{i}",
                    feed=feed,
                )
                for i in range(100)
            ]
            compute_embeddings(articles=articles)
            user = User(id="test_clusters", articles=articles, feeds=[feed])
            session.add(user)
            session.commit()

            assert user.clusters is None

        result = runner.invoke(cli, ["clusters"])

        assert result.exit_code == 0
        assert "Computing clusters" in result.output

        with Session(engine) as session:
            user = session.exec(select(User).filter(User.id == user.id)).one()

            assert user.clusters is not None
            assert len(json.loads(user.clusters)) == 10
            assert user.clusters_updated_at is not None
