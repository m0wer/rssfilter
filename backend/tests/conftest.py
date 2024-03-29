import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session

from app.models.user import User
from app.models.feed import Feed
from app.models.article import Article
from app.routers.common import get_engine
import os
from app.main import app, ROOT_PATH

from sqlmodel.pool import StaticPool
from sqlmodel import create_engine

if not os.path.exists("data"):
    os.makedirs("data")

TEST_USER_ID: str = "test"


@pytest.fixture
def test_user_id():
    return TEST_USER_ID


def setup_db(engine):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(id=TEST_USER_ID)
        feed = Feed(
            id=1,
            url="https://news.ycombinator.com/rss",
            title="Hacker News",
            description="Hacker News RSS feed",
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
