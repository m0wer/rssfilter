from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlmodel import Session, select
from .common import get_engine, RedirectResponseCoder
from src.models.article import Article
from src.models.user import User
from fastapi_cache.decorator import cache

router = APIRouter(
    tags=["log"],
    responses={404: {"description": "Not found"}},
)


# route to log requests to final posts urls and redirect
@router.get("/{user_id}/{article_id}/{link_url:path}")
@cache(expire=300, coder=RedirectResponseCoder)
async def log_post(
    user_id: str, article_id: int, link_url: str, engine=Depends(get_engine)
):
    """Log post, and redirect to the final post url"""
    logger.info(f"User {user_id} is logging link {link_url} from article {article_id}")
    with Session(engine) as session:
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()
        if user is None:
            user = User(id=user_id)
            session.add(user)
        else:
            user.last_request = datetime.now(timezone.utc)
        statement = select(Article).where(Article.id == article_id)
        article = session.exec(statement).first()
        if article is None:
            logger.warning(f"Article {article_id} not found")
            return RedirectResponse(link_url)
        article.updated = datetime.now(timezone.utc)
        session.add(article)

        if article not in user.articles:
            user.articles.append(article)
            session.add(user)

        session.commit()

    return RedirectResponse(link_url)
