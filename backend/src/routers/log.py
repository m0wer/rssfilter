from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlmodel import Session, select
from src.db import engine
from src.models.article import Article
from src.models.user import User
from sqlmodel import Session, select

router = APIRouter(
    prefix="/log",
    tags=["log"],
    responses={404: {"description": "Not found"}},
)


# route to log requests to final posts urls and redirect
@router.get("/{user_id}/{post_url:path}")
async def log_post(user_id, post_url):
    """Log post, and redirect to the final post url"""
    logger.info(f"User {user_id} is logging post {post_url}")
    with Session(engine) as session:
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()
        if user is None:
            user = User(id=user_id)
            session.add(user)
        else:
            user.last_request = datetime.now(timezone.utc)
        statement = select(Article).where(Article.url == post_url)
        article = session.exec(statement).first()
        if article is None:
            article = Article(url=post_url)
            session.add(article)
        else:
            article.updated = datetime.now(timezone.utc)

        if article not in user.articles:
            user.articles.append(article)

        session.commit()
    return RedirectResponse(post_url)
