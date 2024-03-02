# RSS filter

This is a simple RSS filter that filters out unwanted items from an RSS feed. It is written in Python and uses the `feedparser` library to parse the feed.

## Installation

To install the required libraries, run the following command:

```shell
pip install -r requirements.txt
```

## Development

```shell
streamlit run app.py --server.runOnSave true --server.headless true --logger.level=debug --browser.gatherUsageStats=False
```


## Docker

```shell
docker build -t local/rssfilter .
docker run -p 8501:8501 local/rssfilter
```
