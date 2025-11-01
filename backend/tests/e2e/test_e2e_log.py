import pytest
from os import getenv
from urllib.parse import quote

from sqlmodel import Session, select

from app.main import app
from app.models.user import User
from app.models.article import Article


class TestLog:
    @pytest.mark.skipif(
        getenv("REDIS_URL") is None, reason="REDIS_URL environment variable not set"
    )
    def test_log_post(self, client, root_path, engine, test_user_id):
        link_url = "https://www.example.com"
        article_id = 1
        with client:
            response = client.get(
                app.url_path_for(
                    "log_post",
                    link_url=quote(link_url),
                    user_id=test_user_id,
                    article_id=article_id,
                )
            )
        assert response.request.url == link_url

        with Session(engine) as session:
            user = session.exec(select(User).where(User.id == test_user_id)).first()
            assert user is not None

            article = session.exec(
                select(Article).where(Article.id == article_id)
            ).first()
            assert article is not None
            assert article.updated is not None

            assert article in user.articles

    @pytest.mark.skipif(
        getenv("REDIS_URL") is None, reason="REDIS_URL environment variable not set"
    )
    def test_log_post_redirect_with_protocol_in_url(
        self, client, test_user_id, engine, root_path
    ):
        link_url = "https://news.ycombinator.com/item?id=45767178"
        article_id = 1
        response = client.get(
            f"/v1/log/{test_user_id}/{article_id}/{quote(link_url, safe='')}",
            follow_redirects=False,
        )
        assert response.status_code == 307
        location = response.headers.get("location")
        assert location == link_url
        assert location.startswith("https://")
        assert "https://" not in location[8:]
