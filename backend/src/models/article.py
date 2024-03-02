from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import Base64Bytes, BaseModel, Field, HttpUrl


def datetime_now() -> datetime:
    return datetime.now(timezone.utc)


class Article(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    title: str
    body: str
    image: Base64Bytes
    url: HttpUrl
    updated: datetime = Field(default_factory=datetime_now)
