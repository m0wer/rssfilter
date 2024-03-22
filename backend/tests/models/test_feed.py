import pytest

import re

from app.constants import API_BASE_URL, ROOT_PATH
from app.models.article import Article
from app.models.feed import Feed, generate_feed, parse_feed_articles


class TestFeed:
    @pytest.mark.parametrize(
        "feed_string_path",
        [
            "news.ycombinator.com.rss.xml",
            "theverge.com.rss.index.xml",
            "meneame.net.rss.xml",
            "diariodepozuelo.es.xml",
        ],
    )
    def test_parse_feed(self, feed_string_path):
        with open(f"tests/data/{feed_string_path}", "r") as f:
            feed_string = f.read()
        articles = list(parse_feed_articles(feed_string))

        assert articles
        assert len(articles) > 5

    def test_generate_feed(self):
        feed = Feed(
            url="http://example.com/rss.xml",
            title="Test Feed",
            language="en",
            description="Feed description",
        )
        articles = [
            Article(
                title="Test Article",
                url="http://example.com/article",
                description="Test Description",
                comments_url="http://example.com/comments",
            ),
            Article(
                title="Test Article 2",
                url="http://example.com/article2",
                description="Test Description 2",
            ),
        ]

        user_id = "test_user_id"

        generated_feed = generate_feed(feed, articles, user_id)

        assert generated_feed
        assert API_BASE_URL in generated_feed
        assert articles[0].title in generated_feed
        assert articles[1].title in generated_feed

        LOG_URL_PREFIX: str = f"{API_BASE_URL}{ROOT_PATH}/v1/log/{user_id}/"
        FEED_URL_PREFIX: str = f"{API_BASE_URL}{ROOT_PATH}/v1/feed/{user_id}/"

        matches = re.findall(
            r'href=["\']([^"\']+)["\']|<link>([^<]+)</link>|<comments>([^<]+)</comments>',
            generated_feed,
        )

        links = [
            match[0] if match[0] else match[1] if match[1] else match[2]
            for match in matches
        ]

        links_without_log_url_prefix = [
            link
            for link in links
            if not link.startswith(LOG_URL_PREFIX)
            and not link.startswith(FEED_URL_PREFIX)
        ]

        assert not links_without_log_url_prefix, links_without_log_url_prefix
