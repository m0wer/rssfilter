# RSS filter

This is a simple RSS filter that filters out unwanted items from an RSS feed.
It is written in Python and uses the `feedparser` library to parse the feed.

## Dependencies

To install the required libraries, run the following command in the backend or frontend:

```shell
pip install -r requirements.txt
```

## pre-commit

There are some hooks in `.pre-commit-config.yaml` to ensure:
- `pip-compile` is up-to-date with added dependencies
- code is well formatted and linted with `ruff` and `black`


## Docker

There is a `Dockerfile` inside both `frontend` and `backend` folders.
The `backend` image is multistage, thus be careful of building dev or final as `target`.


## docker-compose

The development setup runs on `docker compose` behind a traefik proxy.
The backend is hot-reloaded, while for streamlit changes you need to rebuild the container.

```shell
docker compose up
```


## Roadmap

- [ ] Database
    - [ ] users (id)
    - [ ] feeds (id, url)
    - [ ] users_to_feeds (id, user_id, feed_id)
    - [ ] articles (id, title, body, ~image)
    - [ ] feed_to_articles (id, feed_id, article_id)
- [ ] Some persistance on what articles the user has read
