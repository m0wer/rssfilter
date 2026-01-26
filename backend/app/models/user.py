from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel

from .relations import UserArticleLink, UserFeedLink


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), repr=False
    )
    last_request: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), repr=False
    )
    clusters: str | None = Field(default=None, repr=False)
    clusters_updated_at: datetime | None = Field(default=None, repr=False)
    is_frozen: bool = Field(default=False, index=True)
    frozen_at: datetime | None = Field(default=None, repr=False)

    articles: list["Article"] = Relationship(  # type: ignore  # noqa: F821
        back_populates="users", link_model=UserArticleLink
    )
    feeds: list["Feed"] = Relationship(  # type: ignore  # noqa: F821
        back_populates="users", link_model=UserFeedLink
    )
    feed_links: list["UserFeedLink"] = Relationship(  # type: ignore  # noqa: F821
        back_populates="user", sa_relationship_kwargs={"overlaps": "feeds,users"}
    )
