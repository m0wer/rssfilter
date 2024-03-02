from os import getenv

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from loguru import logger

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/api/v1")

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
    return RedirectResponse(post_url)
