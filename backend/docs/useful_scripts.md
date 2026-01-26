# Useful scripts

## Get recommnedations for a user

```python
def get_engine(self):
    return create_engine(getenv("DATABASE_URL", "sqlite:////tmp/db.sqlite"))

@pytest.mark.skip(reason="WIP")
def test_filter_articles(self):
    with Session(self.get_engine()) as session:
        user = session.exec(
            select(User).where(User.id == "00000000000000000000000000000000")
        ).first()
        read_articles = user.articles
        # get 100 random articles
        random_articles = random.sample(session.exec(select(Article)).all(), 100)
    filtered_articles = filter_articles(read_articles, random_articles)
    breakpoint()
```
