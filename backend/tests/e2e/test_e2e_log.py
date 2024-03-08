from urllib.parse import quote
from src.server import app

from src.models.user import User
from src.models.article import Article

from sqlmodel import Session, select


class TestLog:
    def test_log_post(self, client, root_path, engine):
        user_id = "00000000000000000000000000000000"
        link_url = "https://www.example.com"
        article_id = 1
        with client:
            response = client.get(
                app.url_path_for(
                    "log_post",
                    link_url=quote(link_url),
                    user_id=user_id,
                    article_id=article_id,
                )
            )
        assert response.request.url == link_url

        with Session(engine) as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            assert user is not None

            article = session.exec(
                select(Article).where(Article.id == article_id)
            ).first()
            assert article is not None
            assert article.updated is not None

            assert article in user.articles
