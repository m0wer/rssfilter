from os import getenv

API_BASE_URL = getenv("API_BASE_URL", "https://rssfilter.sgn.space/api").rstrip("/")
ROOT_PATH = getenv("ROOT_PATH", "/").lstrip("/")