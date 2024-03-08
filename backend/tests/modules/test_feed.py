import pytest

import re
from sqlmodel import Session, select

from src.modules.feed import Feed, API_BASE_URL, ROOT_PATH
from src.models.article import Article


class TestFeed:
    @pytest.mark.parametrize(
        "feed_string_path, excluded_links",
        [
            ("news.ycombinator.com.rss.xml", ["https://news.ycombinator.com/"]),
            ("theverge.com.rss.index.xml", ["https://www.theverge.com/"]),
            (
                "meneame.net.rss.xml",
                [
                    "http://www.meneame.net/rss",
                    "http://www.meneame.net",
                    "http://www.meneame.net",
                    "http://pubsubhubbub.appspot.com/",
                ],
            ),
        ],
    )
    def test_get_modified_rss(self, feed_string_path, excluded_links, engine):
        user_id: str = "test_user"

        with open(f"tests/data/{feed_string_path}", "r") as f:
            feed_string = f.read()
        feed = Feed(feed_string=feed_string, engine=engine)
        modified_feed = feed.get_modified_feed(user_id=user_id)
        LOG_URL_PREFIX: str = f"{API_BASE_URL}/{ROOT_PATH}/v1/log/{user_id}/"

        matches = re.findall(
            r'href=["\']([^"\']+)["\']|<link>([^<]+)</link>|<comments>([^<]+)</comments>',
            modified_feed,
        )

        links = [
            match[0] if match[0] else match[1] if match[1] else match[2]
            for match in matches
        ]

        links_without_log_url_prefix = [
            link
            for link in links
            if not link.startswith(LOG_URL_PREFIX) and link not in excluded_links
        ]

        assert not links_without_log_url_prefix, links_without_log_url_prefix

        with Session(engine) as session:
            for link in links:
                if link.startswith(LOG_URL_PREFIX):
                    # article must be in the db
                    article_id = link.split(LOG_URL_PREFIX)[1].split("/")[0]
                    db_article = session.exec(
                        select(Article).where(Article.id == article_id)
                    ).first()
                    assert db_article
