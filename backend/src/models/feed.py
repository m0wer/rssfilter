from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


def datetime_now() -> datetime:
    return datetime.now(timezone.utc)


class Feed(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    url: HttpUrl
    updated: datetime = Field(default_factory=datetime_now)
