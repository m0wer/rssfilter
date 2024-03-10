import xml.etree.ElementTree as ET
import re
from os import getenv
from datetime import datetime
from pydantic import BaseModel
import lxml.etree
from urllib.parse import quote

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Engine
from loguru import logger

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from sqlalchemy.exc import OperationalError


from ..models.article import Article

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/").rstrip("/")
ROOT_PATH = getenv("ROOT_PATH", "/").lstrip("/")


class Feed(BaseModel):
    """Feed parser and modifier.

    This class parses an RSS/Atom feed and has a method to get the modified feed
    with the links replaced by the log API endpoint links.
    """

    model_config = {"arbitrary_types_allowed": True}

    feed_string: str
    engine: Engine

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=0.1, max=1),
        retry=retry_if_exception_type(OperationalError),
    )
    def get_modified_feed(self, user_id: str) -> str:
        """Get the modified feed with the links replaced by the log API endpoint links.

        Returns:
            str: The modified feed.
        """
        parser = lxml.etree.XMLParser(recover=True)
        feed = ET.fromstring(self.feed_string, parser=parser)

        with Session(self.engine) as session:
            for item in feed.findall(".//item") or feed.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            ):
                title = getattr(item.find("title"), "text", None) or getattr(
                    item.find("{http://www.w3.org/2005/Atom}title"), "text", None
                )
                url = getattr(
                    item.find("link"),
                    "text",
                    None,
                ) or getattr(
                    item.find("{http://www.w3.org/2005/Atom}link"),
                    "attrib",
                    {},
                ).get("href")
                comments_url = getattr(
                    item.find("comments"),
                    "text",
                    None,
                ) or getattr(
                    item.find("{http://www.w3.org/2005/Atom}comments"),
                    "text",
                    None,
                )
                description = getattr(
                    item.find("description"),
                    "text",
                    None,
                ) or getattr(
                    item.find("{http://www.w3.org/2005/Atom}content"),
                    "text",
                    None,
                )
                article = Article(
                    title=title,
                    url=url,
                    description=description,
                    comments_url=comments_url,
                )
                session.add(article)
                try:
                    session.commit()
                except IntegrityError:
                    logger.info(
                        f"Object {article} already exists in the database, retrieving it instead."
                    )
                    session.rollback()
                    article = session.exec(select(Article).where(Article.url == url))
                    modified = False
                    if not article.title and title:
                        article.title = title
                        modified = True
                    if not article.description and description:
                        article.description = description
                        modified = True
                    if not article.comments_url and comments_url:
                        article.comments_url = comments_url
                        modified = True
                    if modified:
                        article.updated = datetime.now()
                    session.commit()

                LOG_URL_PREFIX: str = (
                    f"{API_BASE_URL}/{ROOT_PATH}/v1/log/{user_id}/{article.id}"
                )
                if url:
                    if (
                        attr := item.find("{http://www.w3.org/2005/Atom}link")
                    ) is not None:
                        attr.attrib["href"] = f"{LOG_URL_PREFIX}/{quote(url)}"
                    else:
                        item.find("link").text = f"{LOG_URL_PREFIX}/{quote(url)}"
                if comments_url:
                    if item.find("{http://www.w3.org/2005/Atom}comments"):
                        item.find(
                            "{http://www.w3.org/2005/Atom}comments"
                        ).text = f"{LOG_URL_PREFIX}/{quote(comments_url)}"
                    else:
                        item.find(
                            "comments"
                        ).text = f"{LOG_URL_PREFIX}/{quote(comments_url)}"
                # replace all href=... in the description/content
                if description:
                    if item.find("{http://www.w3.org/2005/Atom}content") is not None:
                        for a in item.findall(".//{http://www.w3.org/2005/Atom}a"):
                            a.attrib["href"] = (
                                f"{LOG_URL_PREFIX}/{quote(a.attrib['href'])}"
                            )
                    else:
                        item.find("description").text = re.sub(
                            r'href="(.*?)"',
                            lambda a: f'href="{LOG_URL_PREFIX}/{quote(a.group(1))}"',
                            description,
                        )
        return ET.tostring(feed, encoding="unicode")
