from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel

from .relations import UserArticleLink


class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    url: str = Field(default=None, index=True)
    comments_url: str | None = Field(default=None)
    pub_date: datetime | None = Field(default=None)
    updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    embedding: str | None = Field(default=None)
    feed_id: int = Field(default=None, foreign_key="feed.id")

    users: list["User"] = Relationship(  # type: ignore # noqa: F821
        back_populates="articles", link_model=UserArticleLink
    )
    feed: "Feed" = Relationship(back_populates="articles")  # type: ignore # noqa: F821
