import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session

from src.models.user import User
from src.models.feed import Feed
from src.models.article import Article
from src.routers.common import get_engine
import os
from src.server import app

from sqlmodel.pool import StaticPool
from sqlmodel import create_engine

ROOT_PATH = os.getenv("ROOT_PATH", "/")

if not os.path.exists("data"):
    os.makedirs("data")


def setup_db(engine):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(id="00000000000000000000000000000000")
        feed = Feed(
            id=1,
            url="https://news.ycombinator.com/rss",
            users=[user],
        )
        article = Article(
            id=1,
            title="Test article",
            description="Test description",
            url="https://example.com",
            feed=feed,
            comments_url="https://example.com/comments",
        )
        session.add(user)
        session.add(feed)
        session.add(article)
        session.commit()


@pytest.fixture(scope="function")
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    setup_db(engine)
    yield engine


@pytest.fixture
def client(engine):
    app.dependency_overrides[get_engine] = lambda: engine
    return TestClient(app)


@pytest.fixture
def root_path():
    return ROOT_PATH
