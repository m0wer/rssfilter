from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel

from .relations import UserFeedLink


class Feed(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    url: str = Field(unique=True)
    updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    users: list["User"] = Relationship(  # noqa: F821
        back_populates="feeds", link_model=UserFeedLink
    )
