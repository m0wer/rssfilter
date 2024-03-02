"""Streamlit app to generate a custom filtered RSS feed from an exisitng one.

There is a FastAPI backend that does the actual filtering and the Streamlit app
is used to interact with the user.
"""
import streamlit as st
from loguru import logger
import feedparser
from os import getenv
from uuid import uuid4
from urllib.parse import quote


API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/api/v1/")

logger.info("Streamlit app started")

def get_rss_custom_feed(rss_feed_url: str, uuid: str | None = uuid4().hex) -> str:
    """Get the RSS feed from the URL."""
    return f"{API_BASE_URL}/rss/{uuid}/{quote(rss_feed_url)}"


st.title("RSS Filter")

st.write(
    "Tired of not being able to catch up with all your RSS feeds? "
    "This app will help you filter out the noise and only show you the "
    "articles that you are interested in. Using AI and learning from your "
    "usage patterns. Just provide your exisitng RSS feed and start using the "
    "generated one instead."
)

st.write("Enter the RSS feed URL below")
rss_feed_url = st.text_input("RSS Feed URL")

if rss_feed_url:
    # validate that the URL is a valid RSS feed
    feed = feedparser.parse(rss_feed_url)
    if feed.status != 200:
        logger.info(f"Invalid RSS feed URL: {rss_feed_url}")
        st.alert("Invalid RSS feed URL")
        rss_feed_url = None
    else:
        logger.info(f"RSS feed is valid. Found {len(feed.entries)} entries")
        st.write(f"Here is your custom RSS feed: {get_rss_custom_feed(rss_feed_url)}")
