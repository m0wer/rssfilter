import pytest

import re

from app.constants import API_BASE_URL, ROOT_PATH
from app.models.article import Article
from app.models.feed import Feed, generate_feed, parse_feed_articles, discover_feed_url


class TestFeed:
    @pytest.mark.parametrize(
        "feed_string_path",
        [
            "news.ycombinator.com.rss.xml",
            "theverge.com.rss.index.xml",
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

        log_url_prefix: str = f"{API_BASE_URL}/{ROOT_PATH}/v1/log/{user_id}/"
        feed_url_prefix: str = f"{API_BASE_URL}/{ROOT_PATH}/v1/feed/{user_id}/"

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
            if not link.startswith(log_url_prefix)
            and not link.startswith(feed_url_prefix)
        ]

        assert not links_without_log_url_prefix, links_without_log_url_prefix


class TestDiscoverFeedUrl:
    def test_discover_rss_feed(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <link rel="alternate" type="application/rss+xml" title="RSS" href="/rss">
        </head>
        <body></body>
        </html>
        """
        result = discover_feed_url(html, "https://example.com/")
        assert result == "https://example.com/rss"

    def test_discover_atom_feed(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="alternate" type="application/atom+xml" href="https://example.com/atom.xml">
        </head>
        <body></body>
        </html>
        """
        result = discover_feed_url(html, "https://example.com/")
        assert result == "https://example.com/atom.xml"

    def test_discover_relative_url(self):
        html = """
        <html>
        <head>
            <link rel="alternate" type="application/rss+xml" href="feed.xml">
        </head>
        </html>
        """
        result = discover_feed_url(html, "https://example.com/page/")
        assert result == "https://example.com/page/feed.xml"

    def test_rss_preferred_over_atom(self):
        html = """
        <html>
        <head>
            <link rel="alternate" type="application/rss+xml" href="/rss">
            <link rel="alternate" type="application/atom+xml" href="/atom">
        </head>
        </html>
        """
        result = discover_feed_url(html, "https://example.com/")
        assert result == "https://example.com/rss"

    def test_no_feed_found(self):
        html = """
        <html>
        <head>
            <link rel="stylesheet" href="/styles.css">
        </head>
        <body><p>No feed here</p></body>
        </html>
        """
        result = discover_feed_url(html, "https://example.com/")
        assert result is None

    def test_hackernews_html(self):
        html = """
        <html lang="en" op="news"><head>
        <link rel="alternate" type="application/rss+xml" title="RSS" href="rss">
        <title>Hacker News</title></head>
        <body></body></html>
        """
        result = discover_feed_url(html, "https://news.ycombinator.com/")
        assert result == "https://news.ycombinator.com/rss"

    def test_invalid_html(self):
        html = "not valid html at all <><><"
        result = discover_feed_url(html, "https://example.com/")
        assert result is None
