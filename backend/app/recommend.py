import torch
import random
from transformers import AutoTokenizer, AutoModel
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist
import numpy as np
from rich.progress import track

from loguru import logger

from .models.article import Article


def _batch_compute_embeddings(articles, model, tokenizer):
    texts = [
        (article.title or "") + " " + (article.description or "")
        for article in articles
    ]
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512,
    ).to(model.device)

    with torch.no_grad():
        outputs = model(**inputs)

    embeddings = outputs.pooler_output.cpu().numpy()
    for i, article in enumerate(articles):
        article.embedding = embeddings[i]


def compute_embeddings(
    articles: list[Article], model_name: str = "intfloat/multilingual-e5-large-instruct"
) -> None:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).cuda()

    articles_to_embed = [article for article in articles if article.embedding is None]
    if not articles_to_embed:
        logger.info("All articles already have embeddings.")
        return
    batch_size = 32  # Adjust based on your GPU memory

    for i in track(
        range(0, len(articles_to_embed), batch_size),
        description="Computing embeddings...",
    ):
        batch_articles = articles_to_embed[i : i + batch_size]
        _batch_compute_embeddings(batch_articles, model, tokenizer)


def cluster_articles(articles: list[Article], n_clusters: int) -> KMeans:
    X = np.array([article.embedding for article in articles])
    kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(X)
    return kmeans


def filter_articles(
    articles: list[Article],
    read_articles: list[Article],
    filter_ratio: float = 0.5,
    random_ratio: float = 0.1,
    n_clusters: int = 10,
) -> list[Article]:
    """Filter out articles according to the user's preferences.

    This function tries to return a list of articles that are most relevant to
    the user's interests. It does so by clustering the read articles and then
    calculating the distance of each passed article to the closest cluster. The
    articles are then sorted by this distance and the top `filter_ratio` fraction
    of articles are returned. A small fraction of random articles are also included
    to add some diversity and allow for discovery of new topics.

    If there aren't enough read articles to form clusters, the original list of
    articles is returned identically.

    Args:
        articles: List of articles to filter.
        read_articles: List of articles that the user has read.
        filter_ratio: Fraction of articles to return (default 0.5).
        random_ratio: Fraction of random articles to include (default 0.1).
        n_clusters: Number of clusters to use for clustering (default 10).

    Returns:
        List of articles sorted by relevance
    """
    # Assuming read_articles are not empty and have valid embeddings,
    # you may want to compute_embeddings for them if not already done.
    compute_embeddings(read_articles)

    # Cluster the read articles
    n_clusters = min(
        len(read_articles), 10
    )  # Avoid too many clusters for few articles, adjust as necessary
    kmeans = cluster_articles(read_articles, n_clusters)

    random.shuffle(articles)
    n_random = int(len(articles) * random_ratio)
    random_articles = articles[:n_random]
    del articles[:n_random]

    # Compute missing embeddings for passed articles
    compute_embeddings(articles)

    # Calculate distance of each passed article to the closest cluster
    articles_embeddings = np.array([article.embedding for article in articles])
    distances = cdist(articles_embeddings, kmeans.cluster_centers_, metric="euclidean")
    min_distances = distances.min(axis=1)

    # Sort articles by distance to the closest cluster
    sorted_articles_with_distance = sorted(
        zip(min_distances, articles), key=lambda x: x[0]
    )
    sorted_articles = [article for _, article in sorted_articles_with_distance]

    # Filter out articles based on the filter_ratio
    num_to_filter = int(len(sorted_articles) * filter_ratio)
    return sorted(
        sorted_articles[:num_to_filter] + random_articles,
        key=lambda x: x.pub_date or x.updated,
        reverse=True,
    )
