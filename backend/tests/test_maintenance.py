import sys
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.modules["torch"] = mock.MagicMock()
sys.modules["transformers"] = mock.MagicMock()

import pytest  # noqa: E402
from sqlmodel import Session, create_engine, select  # noqa: E402

from app.cli import SQLModel  # noqa: E402
from app.models.article import Article  # noqa: E402
from app.models.feed import Feed  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture
def engine(tmpdir):
    with mock.patch(
        "app.tasks.ENGINE",
        create_engine(
            f"sqlite:///{tmpdir}/test.db",
            echo=False,
            connect_args={"check_same_thread": False},
        ),
    ) as engine:
        SQLModel.metadata.create_all(engine)
        yield engine


class TestFreezeDormantUsers:
    def test_freeze_dormant_users(self, engine):
        from app.tasks import freeze_dormant_users

        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)

        with Session(engine) as session:
            dormant_user = User(id="dormant", last_request=old_date)
            active_user = User(id="active", last_request=recent_date)
            session.add(dormant_user)
            session.add(active_user)
            session.commit()

        count = freeze_dormant_users()

        assert count == 1
        with Session(engine) as session:
            dormant = session.get(User, "dormant")
            active = session.get(User, "active")
            assert dormant.is_frozen is True
            assert dormant.frozen_at is not None
            assert active.is_frozen is False
            assert active.frozen_at is None

    def test_freeze_does_not_refreeze_already_frozen(self, engine):
        from app.tasks import freeze_dormant_users

        old_date = datetime.now(timezone.utc) - timedelta(days=100)
        frozen_at = datetime.now(timezone.utc) - timedelta(days=50)

        with Session(engine) as session:
            user = User(
                id="already_frozen",
                last_request=old_date,
                is_frozen=True,
                frozen_at=frozen_at,
            )
            session.add(user)
            session.commit()

        count = freeze_dormant_users()
        assert count == 0


class TestUnfreezeUser:
    def test_unfreeze_frozen_user(self, engine):
        from app.tasks import unfreeze_user

        with Session(engine) as session:
            user = User(
                id="frozen_user",
                is_frozen=True,
                frozen_at=datetime.now(timezone.utc) - timedelta(days=10),
            )
            session.add(user)
            session.commit()

        result = unfreeze_user("frozen_user")

        assert result is True
        with Session(engine) as session:
            user = session.get(User, "frozen_user")
            assert user.is_frozen is False
            assert user.frozen_at is None

    def test_unfreeze_non_frozen_user(self, engine):
        from app.tasks import unfreeze_user

        with Session(engine) as session:
            user = User(id="active_user", is_frozen=False)
            session.add(user)
            session.commit()

        result = unfreeze_user("active_user")
        assert result is False

    def test_unfreeze_nonexistent_user(self, engine):
        from app.tasks import unfreeze_user

        result = unfreeze_user("nonexistent")
        assert result is False


class TestCleanupOldArticles:
    def test_cleanup_old_unread_articles(self, engine):
        from app.tasks import cleanup_old_articles

        old_date = datetime.now(timezone.utc) - timedelta(days=200)
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)

        with Session(engine) as session:
            feed = Feed(
                id=1,
                url="https://example.com/feed",
                title="Test Feed",
            )
            old_article = Article(
                id=1,
                title="Old Article",
                description="Old description",
                url="https://example.com/old",
                feed=feed,
                updated=old_date,
            )
            recent_article = Article(
                id=2,
                title="Recent Article",
                description="Recent description",
                url="https://example.com/recent",
                feed=feed,
                updated=recent_date,
            )
            session.add(feed)
            session.add(old_article)
            session.add(recent_article)
            session.commit()

        count = cleanup_old_articles(180)

        assert count == 1
        with Session(engine) as session:
            articles = session.exec(select(Article)).all()
            assert len(articles) == 1
            assert articles[0].id == 2

    def test_cleanup_does_not_delete_read_articles(self, engine):
        from app.tasks import cleanup_old_articles

        old_date = datetime.now(timezone.utc) - timedelta(days=200)

        with Session(engine) as session:
            feed = Feed(
                id=1,
                url="https://example.com/feed",
                title="Test Feed",
            )
            user = User(id="reader")
            old_read_article = Article(
                id=1,
                title="Old Read Article",
                description="Read description",
                url="https://example.com/read",
                feed=feed,
                updated=old_date,
                users=[user],
            )
            session.add(feed)
            session.add(user)
            session.add(old_read_article)
            session.commit()

        count = cleanup_old_articles(180)

        assert count == 0
        with Session(engine) as session:
            articles = session.exec(select(Article)).all()
            assert len(articles) == 1


class TestRemoveOldEmbeddings:
    def test_remove_old_embeddings(self, engine):
        from app.tasks import remove_old_embeddings

        old_date = datetime.now(timezone.utc) - timedelta(days=40)
        recent_date = datetime.now(timezone.utc) - timedelta(days=10)

        with Session(engine) as session:
            feed = Feed(
                id=1,
                url="https://example.com/feed",
                title="Test Feed",
            )
            old_article = Article(
                id=1,
                title="Old Article",
                description="Old description",
                url="https://example.com/old",
                feed=feed,
                updated=old_date,
                embedding="[0.1, 0.2, 0.3]",
            )
            recent_article = Article(
                id=2,
                title="Recent Article",
                description="Recent description",
                url="https://example.com/recent",
                feed=feed,
                updated=recent_date,
                embedding="[0.4, 0.5, 0.6]",
            )
            session.add(feed)
            session.add(old_article)
            session.add(recent_article)
            session.commit()

        count = remove_old_embeddings()

        assert count == 1
        with Session(engine) as session:
            old = session.get(Article, 1)
            recent = session.get(Article, 2)
            assert old.embedding is None
            assert recent.embedding is not None


class TestGetDatabaseStats:
    def test_get_database_stats(self, engine):
        from app.tasks import get_database_stats

        recent_date = datetime.now(timezone.utc) - timedelta(days=10)

        with Session(engine) as session:
            user = User(id="test_stats", last_request=recent_date)
            feed = Feed(
                id=1,
                url="https://example.com/feed",
                title="Test Feed",
            )
            article = Article(
                id=1,
                title="Test Article",
                description="Test description",
                url="https://example.com/article",
                feed=feed,
                embedding="[0.1, 0.2]",
            )
            session.add(user)
            session.add(feed)
            session.add(article)
            session.commit()

        stats = get_database_stats()

        assert stats["users"]["total"] == 1
        assert stats["users"]["active_30d"] == 1
        assert stats["users"]["frozen"] == 0
        assert stats["feeds"]["total"] == 1
        assert stats["articles"]["total"] == 1
        assert stats["articles"]["with_embeddings"] == 1


class TestLogUserActionUnfreeze:
    def test_log_user_action_unfreezes_user(self, engine):
        from app.tasks import log_user_action

        with mock.patch("app.tasks.enqueue_medium_priority"):
            with Session(engine) as session:
                feed = Feed(
                    id=1,
                    url="https://example.com/feed",
                    title="Test Feed",
                )
                article = Article(
                    id=1,
                    title="Test Article",
                    description="Test description",
                    url="https://example.com/article",
                    feed=feed,
                )
                user = User(
                    id="frozen_reader",
                    is_frozen=True,
                    frozen_at=datetime.now(timezone.utc) - timedelta(days=10),
                )
                session.add(feed)
                session.add(article)
                session.add(user)
                session.commit()

            log_user_action("frozen_reader", 1, "https://example.com/article")

            with Session(engine) as session:
                user = session.get(User, "frozen_reader")
                assert user.is_frozen is False
                assert user.frozen_at is None
