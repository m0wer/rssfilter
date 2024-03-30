from fastapi import APIRouter, Response, Depends
from sklearn.decomposition import PCA
import plotly.express as px
from typing import Any
from pydantic import BaseModel
from sqlmodel import Session, select
from loguru import logger
from app.models.user import User
from app.models.article import Article
from app.constants import WEB_URL
from .common import get_engine
import json
import numpy as np
from scipy.spatial.distance import cdist


# from fastapi_cache.coder import PickleCoder
# from fastapi_cache.decorator import cache
from sqlalchemy.orm.exc import NoResultFound

router = APIRouter(
    tags=["user"],
    responses={404: {"description": "Not found"}},
)


class GetUserClustersResponse(BaseModel):
    user_id: str
    clustered_articles: dict[int, list[dict[str, Any]]]


@router.get("/user/{user_id}/clusters")
def get_user_clusters(
    user_id: str, engine=Depends(get_engine)
) -> GetUserClustersResponse:
    with Session(engine, autoflush=False) as session:
        try:
            user: User = session.exec(select(User).where(User.id == user_id)).one()
        except NoResultFound:
            return Response(status_code=404, content=f"User '{user_id}' not found")

        articles_embeddings_list = [
            json.loads(article.embedding)
            for article in user.articles
            if article.embedding
        ]
        if not articles_embeddings_list or not user.clusters:
            logger.warning(
                "No embeddings found for articles. Returning articles as is."
            )
            return Response(
                status_code=503, content="Clusters not ready. Please try again later."
            )
        # Calculate distance of each passed article to the closest cluster
        articles_embeddings = np.array(articles_embeddings_list)
        cluster_centers: list[list[float]] = json.loads(user.clusters)
        distances = cdist(articles_embeddings, cluster_centers, metric="cosine")
        closest_clusters = np.argmin(distances, axis=1)

        # Assign articles to clusters based on the closest cluster
        cluster_articles: list[list[Article]] = [
            [] for _ in range(len(cluster_centers))
        ]
        for i, cluster in enumerate(closest_clusters):
            cluster_articles[cluster].append(user.articles[i])

        return GetUserClustersResponse(
            user_id=user_id,
            clustered_articles={
                cluster_id: [
                    article.model_dump(include={"title", "description", "url"})
                    for article in articles
                ]
                for cluster_id, articles in enumerate(cluster_articles)
            },
        )


@router.get("/user/{user_id}/clusters_2d")
def get_user_clusters_2d(user_id: str, engine=Depends(get_engine)):
    """Return a 2D PNG image of the user's clusters.

    Uses PCA for dimensionality reduction to 2D. WIP.
    """
    with Session(engine, autoflush=False) as session:
        try:
            user: User = session.exec(select(User).where(User.id == user_id)).one()
        except NoResultFound:
            return Response(status_code=404, content=f"User '{user_id}' not found")

        articles_embeddings_list = [
            json.loads(article.embedding)
            for article in user.articles
            if article.embedding
        ]
        if not articles_embeddings_list or not user.clusters:
            logger.warning(
                "No embeddings found for articles. Returning articles as is."
            )
            return Response(
                status_code=503, content="Clusters not ready. Please try again later."
            )
        # Calculate distance of each passed article to the closest cluster
        articles_embeddings = np.array(articles_embeddings_list)
        cluster_centers: list[list[float]] = json.loads(user.clusters)
        distances = cdist(articles_embeddings, cluster_centers, metric="cosine")
        closest_clusters = np.argmin(distances, axis=1)

        # Assign articles to clusters based on the closest cluster
        cluster_articles: list[list[Article]] = [
            [] for _ in range(len(cluster_centers))
        ]
        for i, cluster in enumerate(closest_clusters):
            cluster_articles[cluster].append(user.articles[i])

        # Get the titles of the articles to display in the legend
        article_titles = [article.title for article in user.articles]

        # PCA for dimensionality reduction to 2D
        pca = PCA(n_components=2)
        articles_2d = pca.fit_transform(articles_embeddings)

        # Create the plot
        fig = px.scatter(
            x=articles_2d[:, 0],
            y=articles_2d[:, 1],
            color=[f"Cluster {cluster}" for cluster in closest_clusters],
            text=article_titles,
            labels={"color": "Cluster"},
            title=f"Clusters of your read articles: {WEB_URL}",
        )

        # labels top center
        fig.update_traces(textposition="top center")

        # remove axis labels
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=False)

        return Response(
            content=fig.to_image(format="png", width=1000, height=1000),
            media_type="image/png",
        )
