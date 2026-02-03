[![build](https://github.com/m0wer/rssfilter/actions/workflows/docker.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/docker.yaml)
[![pre-commit](https://github.com/m0wer/rssfilter/actions/workflows/pre-commit.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/pre-commit.yaml)
[![build](https://github.com/m0wer/rssfilter/actions/workflows/test.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/test.yaml)
[![build](https://github.com/m0wer/rssfilter/actions/workflows/monitor.yaml/badge.svg)](https://github.com/m0wer/rssfilter/actions/workflows/monitor.yaml)


# RSS filter

RSS feeds recommendation system based on user read articles. Replaces the feed
URLs with the backend URL and uses the backend to filter out unwanted items
and track user read articles. Uses LLM embeddings and machine learning to
recommend similar articles.

This is a simple RSS filter that filters out unwanted items from an RSS feed.
It is written in Python and uses the `feedparser` library to parse the feed.

It works by tracking the users read articles, computing their embeddings,
clusyering them, and then recommending similar articles from the feed.
It also includes random articles from the feed to allow for discovery of new
topics. This starts working only after a user has read a few articles (10 by
default).

Embedding models allow for a new era of recommendation systems, where a large
user base is not required, since recommendations are based on the content of
the articles, not on other users behavior.


## Self-hosting

You can self-host this project by running the following command:

```shell
cp .env.example .env
docker-compose -f docker-compose.yml up
```

If you don't have or want to use the GPU, first run:

```shell
sed -i 's/^.*devices:.*$/#&/' docker-compose.yaml
```

Test it with:

```shell
curl -X 'GET' \
  'http://localhost/api/v1/feed/1/https%3A%2F%2Fnews.ycombinator.com%2Frss' \
  -H 'accept: application/json'
```

To use the self-hosted frontend, you should change `apiBaseUrl` in
`frontend/static/app.js` to match the backend URL.

### Architecture

The application consists of several services:

- **backend**: FastAPI application serving the API
- **frontend**: Static web frontend
- **redis**: Message queue for background jobs
- **rq-worker**: Background workers for feed fetching and embeddings
- **rq-worker-gpu**: GPU-enabled worker for computing embeddings
- **scheduler**: Handles all periodic tasks (replaces external cron jobs)
- **proxy**: Traefik reverse proxy

### Scheduled Tasks

The scheduler service handles all periodic tasks automatically:

| Task | Schedule | Description |
|------|----------|-------------|
| `fetch_all_feeds` | Hourly | Fetches all feeds for active users |
| `run_full_maintenance` | Daily 4am UTC | Cleanup old articles, vacuum database |
| `retry_disabled_feeds` | Weekly Sunday 3am UTC | Retry feeds that were disabled due to errors |

No external cron jobs are required.

### CLI Commands

The backend includes a CLI for manual operations:

```shell
# Inside the backend container
python -m app.cli --help

# Available commands:
python -m app.cli fetch-feeds      # Manually trigger feed fetching
python -m app.cli retry-feeds      # Re-enable and retry disabled feeds
python -m app.cli maintenance      # Run full maintenance cycle
python -m app.cli stats            # Show database statistics
python -m app.cli freeze-users     # Freeze dormant users
python -m app.cli unfreeze USER_ID # Unfreeze a specific user
python -m app.cli clean-articles   # Delete old unread articles
python -m app.cli clean-embeddings # Remove old embeddings
python -m app.cli vacuum           # Vacuum and analyze database
```

## Development

### Backend

#### Dependencies

To install the required libraries, run the following command in the backend or frontend:

```shell
pip install -r requirements.txt
```

#### Running the backend

```shell
cd backend
python -m uvicorn app.main:app --reload --log-level debug --port 8000
```

## Contributing

There are some hooks in `.pre-commit-config.yaml` to ensure:
- `pip-compile` is up-to-date with added dependencies
- code is well formatted and linted with `ruff` and `black`.

You can install these hooks with `pre-commit install` and run them on demand by `pre-commit run --all-files`.

## Contact

If you have any questions, feel free to contact me at
m0wer at autistici dot org.
