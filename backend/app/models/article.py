from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from .relations import UserArticleLink


class Article(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("url", "feed_id"),)

    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str = Field(repr=False)
    url: str = Field(default=None, index=True)
    comments_url: str | None = Field(default=None, repr=False)
    pub_date: datetime | None = Field(default=None)
    updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), repr=False
    )
    embedding: str | None = Field(default=None, repr=False)
    feed_id: int = Field(default=None, foreign_key="feed.id", index=True, repr=False)

    users: list["User"] = Relationship(  # type: ignore # noqa: F821
        back_populates="articles", link_model=UserArticleLink
    )
    feed: "Feed" = Relationship(back_populates="articles")  # type: ignore # noqa: F821
