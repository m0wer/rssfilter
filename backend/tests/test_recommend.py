from os import getenv
import pytest
import random

from app.recommend import filter_articles
from sqlmodel import create_engine, Session, select


from app.models.article import Article
from app.models.user import User


@pytest.mark.skip(reason="WIP")
class TestRecommend:
    def get_engine(self):
        return create_engine(getenv("DATABASE_URL", "sqlite:////tmp/db.sqlite"))

    def test_filter_articles(self):
        with Session(self.get_engine()) as session:
            user = session.exec(
                select(User).where(User.id == "4f3e1d44738d433c9466deda724d0ad1")
            ).first()
            read_articles = user.articles
            # get 100 random articles
            random_articles = random.sample(session.exec(select(Article)).all(), 100)
        filtered_articles = filter_articles(read_articles, random_articles)
        breakpoint()
