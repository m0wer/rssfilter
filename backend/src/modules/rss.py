import xml.etree.ElementTree as ET
from os import getenv

from loguru import logger

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/").rstrip("/")
ROOT_PATH = getenv("ROOT_PATH", "/api").lstrip("/")


class RSS:
    def __init__(self, feed_string, user_id):
        self.feed_root = ET.fromstring(feed_string)
        self.namespace = self.feed_root.tag.split("}")[0][1:]
        self.user_id = user_id

    def generate_new_link(self, old_link):
        return f"{API_BASE_URL}/{ROOT_PATH}/v1/log/{self.user_id}/{old_link}"

    def find_and_replace_atom_links(self):
        atom_links = self.feed_root.findall(".//{%s}link" % self.namespace)
        for link in atom_links:
            old_link = link.get("href", default=link.text)
            logger.debug("OLD LINK: {link}", link=old_link)
            new_link = self.generate_new_link(old_link)
            logger.debug("NEW LINK: {link}", link=new_link)
            if link.get("href"):
                link.set("href", new_link)
            if link.text:
                link.text = new_link

    def find_and_replace_rss_v2_links(self):
        rss_v2_links = self.feed_root.findall(".//link")
        for link in rss_v2_links:
            old_link = link.get("href", default=link.text)
            logger.debug("OLD LINK: {link}", link=old_link)
            new_link = self.generate_new_link(old_link)
            logger.debug("NEW LINK: {link}", link=new_link)
            if link.get("href"):
                link.set("href", new_link)
            if link.text:
                link.text = new_link

    def get_hackernews_comments(self):
        rss_v2_comments = self.feed_root.findall(".//comments")
        for comment in rss_v2_comments:
            old_link = comment.text
            logger.debug("OLD LINK: {link}", link=old_link)
            new_link = self.generate_new_link(old_link)
            logger.debug("NEW LINK: {link}", link=new_link)
            comment.text = new_link

    def get_hackernews_descriptions(self):
        rss_v2_description = self.feed_root.findall(".//description")
        for description in rss_v2_description:
            if not description.text:
                continue
            description.text = description.text.replace(
                'href="', f'href="{API_BASE_URL}/{ROOT_PATH}/v1/log/{self.user_id}/'
            )

    def get_modified_rss(self):
        self.find_and_replace_atom_links()
        self.find_and_replace_rss_v2_links()
        self.get_hackernews_comments()
        self.get_hackernews_descriptions()
        ET.register_namespace("", self.namespace)
        return ET.tostring(self.feed_root, encoding="unicode")
