from datetime import datetime, timezone
from aiohttp.client_exceptions import ClientError
from pydantic.networks import HttpUrl
from pydantic import validate_call
import xml.etree.ElementTree as ET
from feedgen.feed import FeedGenerator
from collections.abc import Iterator
import feedparser
from aiohttp import ClientTimeout
import aiohttp
from ipaddress import ip_address, IPv4Address, IPv6Address
from socket import gaierror
from contextlib import asynccontextmanager
import os

import re
import dateparser
import lxml.etree
from urllib.parse import quote

from loguru import logger


from sqlmodel import Field, Relationship, SQLModel

from .relations import UserFeedLink
from .article import Article
from ..constants import API_BASE_URL, ROOT_PATH

# Proxy configuration for SSRF protection
# When set, all feed requests go through this proxy, which should only allow external hosts
FEED_PROXY = os.getenv("FEED_PROXY")  # e.g., "http://gluetun:8888"


class Feed(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(unique=True)  # Canonical URL (may be updated after redirects)
    original_url: str | None = Field(
        default=None, index=True
    )  # Original URL user subscribed with (if different from url)
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
    # Error tracking for feed fetching
    consecutive_failures: int = Field(default=0, repr=False)
    last_error: str | None = Field(default=None, repr=False)
    is_disabled: bool = Field(default=False, repr=False)

    users: list["User"] = Relationship(  # type: ignore # noqa: F821
        back_populates="feeds",
        link_model=UserFeedLink,
        sa_relationship_kwargs={"overlaps": "feed,feed_links,user"},
    )
    articles: list["Article"] = Relationship(back_populates="feed")  # type: ignore # noqa: F821
    feed_links: list["UserFeedLink"] = Relationship(  # type: ignore # noqa: F821
        back_populates="feed", sa_relationship_kwargs={"overlaps": "feeds,users"}
    )


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
        fe.link(href=f"{LOG_URL_PREFIX}/{quote(article.url, safe='')}")
        fe.description(
            re.sub(
                r'href="(.*?)"',
                lambda a: f'href="{LOG_URL_PREFIX}/{quote(a.group(1), safe="")}"',
                article.description,
            )
        )
        if article.comments_url:
            fe.comments(f"{LOG_URL_PREFIX}/{quote(article.comments_url, safe='')}")
        if article.pub_date:
            fe.pubDate(article.pub_date.replace(tzinfo=timezone.utc))

    return fg.rss_str(pretty=True).decode("utf-8")


class UpstreamError(Exception):
    pass


class SSRFException(Exception):
    pass


def discover_feed_url(html_content: str, base_url: str) -> str | None:
    """Discover RSS/Atom feed URL from HTML page using link tags."""
    from urllib.parse import urljoin

    try:
        parser = lxml.etree.HTMLParser()
        tree = lxml.etree.fromstring(html_content.encode(), parser)

        for link_type in [
            "application/rss+xml",
            "application/atom+xml",
            "application/feed+json",
        ]:
            links = tree.xpath(f'//link[@rel="alternate"][@type="{link_type}"]/@href')
            if links:
                feed_url = links[0]
                return urljoin(base_url, feed_url)
    except Exception as e:
        logger.debug(f"Failed to parse HTML for feed discovery: {e}")
    return None


def is_safe_ip(ip: str) -> bool:
    """Check if an IP address is safe to connect to (not internal/private)."""
    try:
        addr = ip_address(ip)

        # Block all private, loopback, link-local, multicast, and reserved addresses
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
        ):
            return False

        # Additional IPv4 checks for specific ranges that might not be caught above
        if isinstance(addr, IPv4Address):
            # Block additional ranges:
            # 0.0.0.0/8 (current network)
            # 100.64.0.0/10 (carrier-grade NAT)
            # 198.18.0.0/15 (benchmark testing)
            # 240.0.0.0/4 (reserved for future use)
            if (
                addr.packed[0] == 0  # 0.0.0.0/8
                or (
                    addr.packed[0] == 100 and 64 <= addr.packed[1] <= 127
                )  # 100.64.0.0/10
                or (
                    addr.packed[0] == 198 and addr.packed[1] in [18, 19]
                )  # 198.18.0.0/15
                or addr.packed[0] >= 240
            ):  # 240.0.0.0/4
                return False

        # Additional IPv6 checks
        if isinstance(addr, IPv6Address):
            # Block IPv4-mapped IPv6 addresses that might bypass IPv4 checks
            if addr.ipv4_mapped:
                return is_safe_ip(str(addr.ipv4_mapped))

        return True

    except ValueError:
        # If it's not a valid IP address, let the connection attempt handle it
        # (it will likely fail anyway)
        return True


class SSRFSafeResolverWrapper:
    def __init__(self):
        self._resolver = aiohttp.AsyncResolver()

    async def resolve(self, host, port, family):
        try:
            addresses = await self._resolver.resolve(host, port, family)
            for addr in addresses:
                if not is_safe_ip(addr["host"]):
                    logger.warning(f"SSRF attempt blocked for {addr['host']}")
                    raise SSRFException(
                        "Access to internal network resources is not allowed"
                    )
            return addresses
        except gaierror:
            # This can happen for various reasons, including host not found.
            # We'll let the ClientSession handle the error.
            return []


@asynccontextmanager
async def ssrf_safe_session(**kwargs):
    """Create a session with SSRF protection.

    SSRF protection strategy:
    - If FEED_PROXY is set: Route all requests through the proxy.
      The proxy (e.g., gluetun) should be configured to only allow external hosts.
    - If no proxy: Use DNS resolution validation to block private IPs.
    """
    if FEED_PROXY:
        # Proxy handles SSRF protection - no need for custom resolver
        logger.debug(f"Using proxy for feed requests: {FEED_PROXY}")
        async with aiohttp.ClientSession(**kwargs) as session:
            yield session
    else:
        # No proxy - use custom resolver to validate IPs
        connector = aiohttp.TCPConnector(resolver=SSRFSafeResolverWrapper())
        async with aiohttp.ClientSession(connector=connector, **kwargs) as session:
            yield session


def validate_url_not_ip(url: str) -> None:
    """Validate that a URL doesn't point directly to a private IP.

    This is a defense-in-depth check. When using a proxy, the proxy
    handles the actual SSRF protection.
    """
    # Skip validation if using proxy (proxy handles SSRF protection)
    if FEED_PROXY:
        return

    from urllib.parse import urlparse

    parsed_url = urlparse(url)

    try:
        if parsed_url.hostname and not is_safe_ip(parsed_url.hostname):
            logger.warning(f"SSRF attempt blocked for IP: {parsed_url.hostname}")
            raise SSRFException("Access to internal network resources is not allowed")
    except (ValueError, TypeError):
        pass


async def _fetch_url(
    session: aiohttp.ClientSession,
    url: str,
    max_redirects: int = 10,
) -> tuple[str, str]:
    """Fetch URL content with SSRF protection, following all redirects.

    All redirects to external hosts are allowed. SSRF protection is provided by:
    1. If FEED_PROXY is set: requests go through the proxy which only allows external hosts
    2. Without proxy: SSRFSafeResolverWrapper validates DNS resolution for each request,
       blocking any that resolve to private/internal IPs

    Returns:
        Tuple of (content, final_url) - final_url may differ if redirects occurred.
    """
    validate_url_not_ip(url)
    try:
        async with session.get(
            url,
            headers={"User-agent": "Mozilla/5.0"},
            allow_redirects=True,
            max_redirects=max_redirects,
            proxy=FEED_PROXY,  # None if not set, aiohttp ignores None
        ) as response:
            # Validate the final URL after redirects (defense in depth)
            final_url = str(response.url)
            validate_url_not_ip(final_url)
            response.raise_for_status()
            return await response.text(), final_url
    except aiohttp.TooManyRedirects:
        raise UpstreamError(f"Too many redirects (max {max_redirects})")
    except ClientError as e:
        raise UpstreamError(f"Error fetching feed: {e}") from e
    except SSRFException:
        raise


@validate_call
async def parse_feed(feed_url: HttpUrl) -> Feed:
    """Register a new feed.

    If the URL points to an HTML page, attempts to discover the RSS/Atom feed URL
    from <link rel="alternate"> tags.

    Note: The returned Feed's url field will be the final URL after any redirects,
    which may differ from the input feed_url.
    """
    validate_url_not_ip(str(feed_url))

    async with ssrf_safe_session(timeout=ClientTimeout(total=20)) as aiohttp_session:
        feed_response, final_url = await _fetch_url(aiohttp_session, str(feed_url))

        parsed = feedparser.parse(feed_response)
        if not parsed.get("feed") or not parsed.feed.get("title"):
            discovered_url = discover_feed_url(feed_response, str(feed_url))
            if discovered_url:
                logger.info(
                    f"Discovered feed URL {discovered_url} from HTML page {feed_url}"
                )
                feed_response, final_url = await _fetch_url(
                    aiohttp_session, discovered_url
                )
                parsed = feedparser.parse(feed_response)
                if not parsed.get("feed") or not parsed.feed.get("title"):
                    raise UpstreamError(
                        f"Discovered feed URL {discovered_url} is not a valid feed."
                    )
            else:
                raise UpstreamError(
                    "URL is not a valid RSS/Atom feed and no feed link was found in the page."
                )

    feed = Feed(
        url=final_url,  # Use the final URL after redirects
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
