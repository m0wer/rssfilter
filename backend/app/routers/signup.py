from fastapi import UploadFile
from fastapi import APIRouter, Response, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from loguru import logger
from app.models.user import User
from .common import get_engine
from ..constants import API_BASE_URL, ROOT_PATH
from uuid import uuid4

from lxml import etree

# from fastapi_cache.coder import PickleCoder
# from fastapi_cache.decorator import cache
from sqlalchemy.orm.exc import NoResultFound

router = APIRouter(
    tags=["signup"],
    responses={404: {"description": "Not found"}},
)


class ResgisterUserResponse(BaseModel):
    user_id: str


@router.post("/user", status_code=201)
def register_user(engine=Depends(get_engine)) -> ResgisterUserResponse:
    user_id: str = uuid4().hex
    with Session(engine, autoflush=False) as session:
        try:
            user: User = session.exec(select(User).where(User.id == user_id)).one()
        except NoResultFound:
            logger.info(f"User {user_id} not found in database, creating new user")
            user = User(id=user_id)
            session.add(user)
            try:
                session.commit()
            except Exception as e:
                # might happen if the user was created before by another thread
                logger.warning(f"Failed to add user {user_id} to database: {e}")
                session.rollback()
                user = session.exec(select(User).where(User.id == user_id)).one()
        return ResgisterUserResponse(user_id=user.id)


def get_rss_custom_feed(rss_feed_url: str, uuid: str | None = uuid4().hex) -> str:
    """Get the RSS feed from the URL."""
    return (
        f"{API_BASE_URL}/{ROOT_PATH}/v1/feed/{uuid}/{rss_feed_url}"
        if ROOT_PATH
        else f"{API_BASE_URL}/v1/feed/{uuid}/{rss_feed_url}"
    )


def get_opml_custom(opml_text: str, uuid: str | None = None) -> str:
    """Get the OPML file with custom RSS feeds."""
    tree = etree.fromstring(opml_text.encode("utf-8"))
    root = tree.getroottree()

    for outline in root.findall(".//outline"):
        if outline.get("type") != "rss":
            continue
        url = outline.get("xmlUrl")
        if url is None:
            continue
        new_url = (
            get_rss_custom_feed(url) if uuid is None else get_rss_custom_feed(url, uuid)
        )
        outline.set("xmlUrl", new_url)  # Update the XML attribute with the new URL

    return etree.tostring(
        tree, pretty_print=True, xml_declaration=True, encoding="utf-8"
    ).decode("utf-8")


@router.post("/process_opml")
def process_opml(
    opml: UploadFile, user_id: str | None = None, engine=Depends(get_engine)
):
    if user_id is None:
        user_id = uuid4().hex
    with Session(engine, autoflush=False) as session:
        try:
            user: User = session.exec(select(User).where(User.id == user_id)).one()
        except NoResultFound:
            logger.info(f"User {user_id} not found in database, creating new user")
            user = User(id=user_id)
            session.add(user)
            try:
                session.commit()
            except Exception as e:
                # might happen if the user was created before by another thread
                logger.warning(f"Failed to add user {user_id} to database: {e}")
                session.rollback()
                user = session.exec(select(User).where(User.id == user_id)).one()
    opml_text = opml.file.read().decode("utf-8")
    opml_text = get_opml_custom(opml_text)

    return Response(content=opml_text, media_type="application/xml")
