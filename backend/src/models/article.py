from datetime import datetime, timezone

from sqlmodel import SQLModel, Relationship, Field

from .relations import UserArticleLink

class Article(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str | None = Field(default=None)
    description: str | None = None
    url: str = Field(index=True)
    updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    users: list["User"] = Relationship(
        back_populates="articles", link_model=UserArticleLink
    )
