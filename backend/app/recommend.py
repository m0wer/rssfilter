import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist
import numpy as np

from .models.article import Article


def compute_embeddings(
    articles: list[Article], model_name: str = "intfloat/multilingual-e5-large-instruct"
) -> None:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    for article in articles:
        inputs = tokenizer(
            (article.title or "") + " " + (article.description or ""),
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        with torch.no_grad():
            outputs = model(**inputs)
        article.embedding = outputs.pooler_output[0].numpy()


def cluster_articles(articles: list[Article], n_clusters: int) -> KMeans:
    X = np.array([article.embedding for article in articles])
    kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(X)
    return kmeans


def filter_articles(
    articles: list[Article], read_articles: list[Article], filter_ratio: float = 0.5
) -> list[Article]:
    # Assuming read_articles are not empty and have valid embeddings,
    # you may want to compute_embeddings for them if not already done.
    compute_embeddings(read_articles)

    # Cluster the read articles
    n_clusters = min(
        len(read_articles), 10
    )  # Avoid too many clusters for few articles, adjust as necessary
    kmeans = cluster_articles(read_articles, n_clusters)

    # Compute embeddings for passed articles
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
    return sorted_articles[:num_to_filter]
