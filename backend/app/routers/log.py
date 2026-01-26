from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from .common import get_engine, RedirectResponseCoder
from app.tasks import enqueue_medium_priority, log_user_action
from fastapi_cache.decorator import cache

router = APIRouter(
    tags=["log"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}/{article_id}/{link_url:path}")
@cache(expire=300, coder=RedirectResponseCoder)
async def log_post(
    request: Request,
    user_id: str,
    article_id: int,
    link_url: str,
    engine=Depends(get_engine),
):
    """Log post, and redirect to the final post url"""
    if request.query_params:
        link_url = f"{link_url}?"
        for key, value in request.query_params.items():
            link_url = f"{link_url}&{key}={value}"

    enqueue_medium_priority(log_user_action, user_id, article_id, link_url)
    return RedirectResponse(link_url)
