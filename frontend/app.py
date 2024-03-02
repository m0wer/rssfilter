"""Streamlit app to generate a custom filtered RSS feed from an exisitng one.

There is a FastAPI backend that does the actual filtering and the Streamlit app
is used to interact with the user.
"""

from os import getenv
from uuid import uuid4

import feedparser
import streamlit as st
from loguru import logger
from lxml import etree

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/api/v1").rstrip("/")

logger.info("Streamlit app started")


def get_rss_custom_feed(rss_feed_url: str, uuid: str | None = uuid4().hex) -> str:
    """Get the RSS feed from the URL."""
    return f"{API_BASE_URL}/feed/{uuid}/{rss_feed_url}"


st.title("RSS Filter")

st.write(
    "Tired of not being able to catch up with all your RSS feeds? "
    "This app will help you filter out the noise and only show you the "
    "articles that you are interested in. Using AI and learning from your "
    "usage patterns. Just provide your existing RSS feed and start using the "
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


def get_opml_custom(opml_text: str, uuid: str | None = None) -> str:
    """Get the OPML file with custom RSS feeds."""
    # ValueError: Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
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


# Add option to upload an OPML file with multiple feeds
uploaded_file = st.file_uploader("Upload an OPML file", type="opml")

if uploaded_file is not None:
    uuid: str = uuid4().hex
    custom_opml = get_opml_custom(uploaded_file.getvalue().decode("utf-8"), uuid)
    # Create a download button for the new OPML file
    st.download_button(
        "Download your new OPML file", custom_opml, f"rssfilter-{uuid}.opml"
    )
