from sqlmodel import Field, SQLModel


class UserArticleLink(SQLModel, table=True):
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)
    article_id: int | None = Field(
        default=None, foreign_key="article.id", primary_key=True
    )


class UserFeedLink(SQLModel, table=True):
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)
    feed_id: int | None = Field(default=None, foreign_key="feed.id", primary_key=True)
