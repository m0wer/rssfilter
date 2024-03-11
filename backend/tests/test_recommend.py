import random

from app.recommend import filter_articles
from sqlmodel import create_engine, Session, select


from app.models.article import Article
from app.models.user import User


class TestRecommend:
    def get_engine(self):
        return create_engine("sqlite:////tmp/db.sqlite")

    def test_filter_articles(self):
        with Session(self.get_engine()) as session:
            read_articles = (
                session.exec(
                    select(User).where(User.id == "4f3e1d44738d433c9466deda724d0ad1")
                )
                .first()
                .articles
            )
            # get 100 random articles
            random_articles = random.sample(session.exec(select(Article)).all(), 100)
        filtered_articles = filter_articles(read_articles, random_articles)
        breakpoint()
