from sqlmodel import Field, SQLModel
from datetime import datetime, timezone


class UserArticleLink(SQLModel, table=True):
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)
    article_id: int | None = Field(
        default=None, foreign_key="article.id", primary_key=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), primary_key=True
    )


class UserFeedLink(SQLModel, table=True):
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)
    feed_id: int | None = Field(default=None, foreign_key="feed.id", primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), primary_key=True
    )
