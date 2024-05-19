from datetime import datetime, timezone
from aiohttp.client_exceptions import ClientError
from pydantic.networks import HttpUrl
import xml.etree.ElementTree as ET
from feedgen.feed import FeedGenerator
from collections.abc import Iterator
import feedparser
from aiohttp import ClientSession

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
    logo: str | None = Field(repr=False)
    description: str | None = Field(default=None, repr=False)
    language: str | None = Field(default=None, repr=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), repr=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), repr=False
    )

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
    logger.debug(f"Generating custom feed for {feed.url}, for user {user_id}")
    fg = FeedGenerator()
    fg.id(feed.url)
    fg.title(feed.title)
    fg.description(feed.description or feed.title)
    fg.logo(feed.logo)
    fg.link(
        # TODO: doesn't work with empty ROOT_PATH
        href=f"{API_BASE_URL}/{ROOT_PATH}/v1/feed/{user_id}/{feed.url}",
        rel="self",
    )
    fg.language(feed.language)
    for article in articles:
        logger.debug(f"Replacing links for article: {article}")
        LOG_URL_PREFIX: str = (
            f"{API_BASE_URL}/{ROOT_PATH}/v1/log/{user_id}/{article.id}"
        )
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


class UpstreamError(Exception):
    pass


async def parse_feed(feed_url: HttpUrl) -> Feed:
    """Register a new feed."""
    if feed_url.host and re.match(
        r"^(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b", feed_url.host
    ):
        raise RuntimeError("Invalid URL")
    async with ClientSession() as aiohttp_session:
        try:
            async with aiohttp_session.get(
                str(feed_url),
                headers={"User-agent": "Mozilla/5.0"},
                allow_redirects=False,
            ) as response:
                response.raise_for_status()
                feed_response = await response.text()
        except ClientError as e:
            raise UpstreamError(f"Error fetching feed: {e}") from e
    parsed = feedparser.parse(feed_response)
    if not parsed.get("feed") or not parsed.feed.get("title"):
        raise UpstreamError("Incorrect feed format.")
    feed = Feed(
        url=str(feed_url),
        title=parsed.feed.get("title"),
        description=parsed.feed.get("description"),
        logo=parsed.feed.get("logo"),
        language=parsed.feed.get("language"),
        articles=[
            Article(
                title=entry.title,
                url=entry.link,
                description=entry.description,
                comments_url=entry.get("comments"),
                pub_date=dateparser.parse(entry.published)
                if hasattr(entry, "published")
                else datetime.now(),
            )
            for entry in parsed.entries
        ],
    )
    return feed
