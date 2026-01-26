import pytest
import re
import asyncio
from os import getenv

from aiohttp import ClientSession, ClientTimeout

API_URL: str

if not (API_URL := getenv("API_URL")):  # type: ignore
    pytestmark = pytest.mark.skip(reason="API_URL not set")

user_id: str = "test"
# feed: (status code, is valid)
user_feeds: dict[str, tuple[int, bool]] = {
    "https://xkcd.com/rss.xml": (200, True),
    "https://www.reddit.com/r/programming.rss": (200, True),
    # "https://www.theverge.com/rss/index.xml": (200, True),
    "https://google.com": (502, False),
    "https://example.com/404": (502, False),
}

LOG_URL_PREFIX: str = f"{API_URL}/v1/log/{user_id}/"
FEED_URL_PREFIX: str = f"{API_URL}/v1/feed/{user_id}/"


class TestGetFeeds:
    """Test the main use case: getting feeds.

    As a user, I want to retrieve all my feeds at once to get the latest articles.

    This requires:
        - Registering the user in the DB
        - Registering the user feeds that weren't already in the DB
        - Fetching the feeds
        - Returning the feeds, replacing the links with the custom tracker ones

    Tricky parts:
        - Concurrency in the first batch of requests, when the user does not
          exist yet and thus has to be created.
        - Same but for the feeds.
        - Duplicated articles but from different feeds.
        - Feeds upstream errors.
        - ...
    """

    @pytest.mark.asyncio
    async def test_get_feeds_new_user(self):
        """Test the main use case with a new user."""
        async with ClientSession(timeout=ClientTimeout(total=10)) as session:
            # get all feeds at once
            results = await asyncio.gather(
                *[
                    session.get(f"{FEED_URL_PREFIX}{feed_url}")
                    for feed_url in user_feeds.keys()
                ]
            )
            for i, result in enumerate(results):
                assert result.status == user_feeds[list(user_feeds.keys())[i]][0], (
                    await result.text()
                )

            # should still work the second time (no new user or feed created), might be cached, ...
            results2 = await asyncio.gather(
                *[
                    session.get(f"{FEED_URL_PREFIX}{feed_url}")
                    for feed_url in user_feeds.keys()
                ]
            )
            for i, result in enumerate(results2):
                assert result.status == user_feeds[list(user_feeds.keys())[i]][0], (
                    await result.text()
                )

            # mark some articles as read by visiting their links
            for i, result in enumerate(results2):
                if user_feeds[list(user_feeds.keys())[i]][1]:
                    link_match = re.search(r"<link>(.+?)</link>", await result.text())
                    link_response = await session.get(link_match.group(1))
                    assert link_response.status == 200, await link_response.text()

                    # now the comments link
                    comments_match = re.search(
                        r"<comments>(.+?)</comments>", await result.text()
                    )
                    if comments_match:
                        comments_response = await session.get(comments_match.group(1))
                        assert comments_response.status == 200, (
                            await comments_response.text()
                        )
