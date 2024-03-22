import pytest

from urllib.parse import quote
from app.main import app

from app.models.feed import Feed
from app.models.user import User
from app.models.article import Article

from sqlmodel import Session, select


class TestFeed:
    @pytest.mark.parametrize(
        "feed_url,has_comments",
        [
            ("https://news.ycombinator.com/rss", True),
            (
                "https://www.diariodepozuelo.es/index.php?"
                "option=com_joomrss&task=feed&id=2:noticias-destacadas-en-diario-de-pozuelo"
                "&format=feed&Itemid=5196",
                False,
            ),
        ],
    )
    def test_get_feed(self, client, root_path, engine, feed_url, has_comments):
        user_id = "00000000000000000000000000000000"
        with client:
            response = client.get(
                app.url_path_for("get_feed", feed_url=quote(feed_url), user_id=user_id)
            )
        assert response.status_code == 200
        assert response.text.startswith("<?xml version='1.0' encoding='UTF-8'?>")
        assert f"/log/{user_id}" in response.text

        with Session(engine) as session:
            feed = session.exec(select(Feed).where(Feed.url == feed_url)).one()
            assert feed
            assert feed.url == feed_url

            user = session.exec(select(User).where(User.id == user_id)).one()
            assert user
            assert user.id == user_id
            assert feed in user.feeds
            assert user in feed.users

            articles = session.exec(select(Article)).all()
            assert articles
            for article in articles:
                assert article.title
                assert article.url
                assert article.description
                assert article.updated
                if has_comments:
                    assert article.comments_url

    def test_get_feed_not_found(self, client, root_path):
        user_id = "00000000000000000000000000000000"
        with client:
            response = client.get(
                app.url_path_for(
                    "get_feed",
                    feed_url=quote("https://example.com/404"),
                    user_id=user_id,
                )
            )
        assert response.status_code == 502

    def test_get_feed_invalid_url(self, client, root_path):
        user_id = "00000000000000000000000000000000"
        with client:
            response = client.get(
                app.url_path_for("get_feed", feed_url="invalid", user_id=user_id)
            )
        assert response.status_code == 422
