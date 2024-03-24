from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel

from .relations import UserArticleLink, UserFeedLink


class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    first_request: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), repr=False
    )
    last_request: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), repr=False
    )

    articles: list["Article"] = Relationship(  # type: ignore  # noqa: F821
        back_populates="users", link_model=UserArticleLink
    )
    feeds: list["Feed"] = Relationship(  # type: ignore  # noqa: F821
        back_populates="users", link_model=UserFeedLink
    )
