from os import getenv

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/").rstrip("/")
ROOT_PATH = getenv("ROOT_PATH", "/").lstrip("/").rstrip("/")

WEB_URL = getenv("WEB_URL", "https://rssfilter.sgn.space/").rstrip("/")
