from urllib.parse import quote
from src.server import app

from src.models.feed import Feed
from src.models.user import User
from src.models.article import Article

from sqlmodel import Session, select


class TestFeed:
    def test_get_feed(self, client, root_path, engine):
        user_id = "00000000000000000000000000000000"
        feed_url = "https://news.ycombinator.com/rss"
        with client:
            response = client.get(
                app.url_path_for("get_feed", feed_url=quote(feed_url), user_id=user_id)
            )
        assert response.status_code == 200
        assert response.text.startswith('<rss version="2.0">')
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
                assert article.comments_url
