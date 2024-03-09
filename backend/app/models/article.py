from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel

from .relations import UserArticleLink


class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str | None = Field(default=None)
    description: str | None = None
    url: str | None = Field(default=None, index=True)
    comments_url: str | None = Field(default=None)
    updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    users: list["User"] = Relationship(  # noqa: F821
        back_populates="articles", link_model=UserArticleLink
    )
