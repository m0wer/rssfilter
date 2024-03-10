from datetime import datetime, timezone

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from fastapi import APIRouter, Response, Depends
from sqlmodel import Session, select
from app.models.feed import Feed
from app.models.user import User
from app.modules.feed import Feed as FeedModule
from .common import get_engine, XMLCoder
from fastapi_cache.decorator import cache

router = APIRouter(
    tags=["feed"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}/{feed_url:path}")
@cache(expire=300, coder=XMLCoder)
async def get_feed(user_id, feed_url, engine=Depends(get_engine)) -> str:
    """Get filtered feed."""
    with Session(engine) as session:
        statement = select(User).where(User.id == user_id)
        user = session.exec(statement).first()
        if user is None:
            user = User(id=user_id)
            session.add(user)
        else:
            user.last_request = datetime.now(timezone.utc)
        statement = select(Feed).where(Feed.url == feed_url)
        feed_module = session.exec(statement).first()
        if feed_module is None:
            feed_module = Feed(url=feed_url)
            session.add(feed_module)
        else:
            feed_module.updated = datetime.now(timezone.utc)
        if feed_module not in user.feeds:
            user.feeds.append(feed_module)
        session.commit()

    async with ClientSession() as session:
        try:
            async with session.get(
                feed_url, headers={"User-agent": "Mozilla/5.0"}
            ) as response:
                # pass through non 2xx status codes
                if response.status // 100 != 2:
                    return Response(
                        content=await response.text(), status_code=response.status
                    )
                feed_response = await response.text()
        except ClientError as e:
            return Response(content=str(e), status_code=502)
    feed_module = FeedModule(feed_string=feed_response, engine=engine)
    modified_feed = feed_module.get_modified_feed(user_id=user_id)
    return Response(content=modified_feed, media_type="application/xml")
