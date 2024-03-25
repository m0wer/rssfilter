[![build](https://github.com/m0wer/rssfilter/actions/workflows/docker.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/docker.yaml)
[![pre-commit](https://github.com/m0wer/rssfilter/actions/workflows/pre-commit.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/pre-commit.yaml)
[![build](https://github.com/m0wer/rssfilter/actions/workflows/test.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/test.yaml)
[![build](https://github.com/m0wer/rssfilter/actions/workflows/monitor.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/monitor.yaml)


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
- code is well formatted and linted with `ruff` and `black`.

You can install these hooks with `pre-commit install` and run them on demand by `pre-commit run --all-files`.


## Docker

There is a `Dockerfile` inside both `frontend` and `backend` folders.
The `backend` image is multistage, thus be careful of building dev or final as `target`.

## docker-compose

```shell
docker compose up
```

Now you can access http://localhost on port 80, where traefik will redirect
`/` to the frontend and `/api` to the backend (without stripping the prefix)

## Development

```shell
cd backend
python -m uvicorn app.main:app --reload --log-level debug --port 8000
```
