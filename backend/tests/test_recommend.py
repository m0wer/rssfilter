from app.recommend import filter_articles, cluster_articles, compute_embeddings


from app.models.article import Article


class TestRecommend:
    def test_filter_articles_dummy_data(self):
        read_articles = [
            Article(
                id=1,
                title="Everything about apples",
                description="Apples are a great fruit, healthy and tasty",
            ),
            Article(
                id=2,
                title="The best way to eat apples",
                description="Apples are great, but how to eat them?",
            ),
            Article(
                id=3,
                title="Receta de compota de manzana",
                description="Fácil receta para hace en casa tu propia compota de manzana",
            ),
        ]
        articles_to_filter = [
            Article(
                id=4,
                title="Apple crumble recipe",
                description="Easy recipe to make apple crumble at home",
            ),
            Article(
                id=5,
                title="Estoicism",
                description="Stay calm and carry on",
            ),
        ]
        compute_embeddings(articles=read_articles)
        compute_embeddings(articles=articles_to_filter)
        kmeans = cluster_articles(articles=read_articles, n_clusters=1)
        filtered_articles = filter_articles(
            articles=articles_to_filter,
            cluster_centers=kmeans.cluster_centers_,
            filter_ratio=0.5,
            random_ratio=0,
        )
        assert len(filtered_articles) == 1
        assert filtered_articles[0].id == 4
