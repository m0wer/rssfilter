import os
import sys
from unittest import mock

import numpy as np


def create_torch_mock():
    torch_mock = mock.MagicMock()
    torch_mock.cuda.is_available.return_value = False
    torch_mock.no_grad.return_value.__enter__ = mock.MagicMock()
    torch_mock.no_grad.return_value.__exit__ = mock.MagicMock()
    return torch_mock


def create_transformers_mock():
    transformers_mock = mock.MagicMock()

    def mock_tokenizer_call(*args, **kwargs):
        result = mock.MagicMock()
        result.to.return_value = result
        return result

    tokenizer_instance = mock.MagicMock()
    tokenizer_instance.side_effect = mock_tokenizer_call
    tokenizer_instance.return_value = mock.MagicMock()
    tokenizer_instance.return_value.to.return_value = tokenizer_instance.return_value
    transformers_mock.AutoTokenizer.from_pretrained.return_value = tokenizer_instance

    embedding_counter = {"count": 0}

    def mock_model_call(*args, **kwargs):
        outputs = mock.MagicMock()
        batch_size = 3
        embedding_dim = 1024
        base = embedding_counter["count"]
        embeddings = np.random.RandomState(42 + base).randn(batch_size, embedding_dim)
        embedding_counter["count"] += batch_size
        outputs.pooler_output.cpu.return_value.numpy.return_value = embeddings
        return outputs

    model_instance = mock.MagicMock()
    model_instance.side_effect = mock_model_call
    model_instance.device = "cpu"
    transformers_mock.AutoModel.from_pretrained.return_value = model_instance

    return transformers_mock


sys.modules["torch"] = create_torch_mock()
sys.modules["transformers"] = create_transformers_mock()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel, Session, create_engine  # noqa: E402
from sqlmodel.pool import StaticPool  # noqa: E402

from app.main import app, ROOT_PATH  # noqa: E402
from app.models.article import Article  # noqa: E402
from app.models.feed import Feed  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routers.common import get_engine  # noqa: E402

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
