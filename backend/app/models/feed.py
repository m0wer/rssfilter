from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from feedgen.feed import FeedGenerator
from collections.abc import Iterator

import re
import dateparser
import lxml.etree
from urllib.parse import quote

from loguru import logger


from sqlmodel import Field, Relationship, SQLModel

from .relations import UserFeedLink
from .article import Article
from ..constants import API_BASE_URL, ROOT_PATH


class Feed(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(unique=True)
    title: str
    logo: str | None = None
    description: str
    language: str | None = None
    updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    users: list["User"] = Relationship(  # type: ignore # noqa: F821
        back_populates="feeds", link_model=UserFeedLink
    )
    articles: list["Article"] = Relationship(back_populates="feed")  # type: ignore # noqa: F821


def parse_feed_articles(feed_string) -> Iterator[Article]:
    """Parse the feed and return a list of articles.

    Returns:
        The list of articles.
    """
    parser = lxml.etree.XMLParser(recover=True)
    feed = ET.fromstring(feed_string, parser=parser)

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
        if (
            date_str := getattr(
                item.find("pubDate"),
                "text",
                None,
            )
            or getattr(
                item.find("{http://www.w3.org/2005/Atom}published"),
                "text",
                None,
            )
        ) is not None:
            pub_date = dateparser.parse(date_str)
        else:
            pub_date = None
        article = Article(
            title=title,
            url=url,
            description=description,
            comments_url=comments_url,
            pub_date=pub_date,
        )
        yield article


def generate_feed(feed: Feed, articles: list[Article], user_id: str) -> str:
    """Get the modified feed with the links replaced by the log API endpoint links.

    Returns:
        str: The modified feed.
    """
    fg = FeedGenerator()
    fg.id(feed.url)
    fg.title(feed.title)
    fg.description(feed.description or feed.title)
    fg.logo("http://ex.com/logo.jpg")
    fg.link(
        href=f"{API_BASE_URL}{ROOT_PATH}/v1/feed/{user_id}/{feed.url}",
        rel="self",
    )
    fg.language(feed.language)
    for article in articles:
        logger.debug(f"Parsing article: {article}")
        LOG_URL_PREFIX: str = f"{API_BASE_URL}{ROOT_PATH}/v1/log/{user_id}/{article.id}"
        fe = fg.add_entry()
        fe.id(article.url)
        fe.title(article.title)
        fe.link(href=f"{LOG_URL_PREFIX}/{quote(article.url)}")
        fe.description(
            re.sub(
                r'href="(.*?)"',
                lambda a: f'href="{LOG_URL_PREFIX}/{quote(a.group(1))}"',
                article.description,
            )
        )
        if article.comments_url:
            fe.comments(f"{LOG_URL_PREFIX}/{quote(article.comments_url)}")
        if article.pub_date:
            fe.pubDate(article.pub_date.replace(tzinfo=timezone.utc))

    return fg.rss_str(pretty=True).decode("utf-8")
