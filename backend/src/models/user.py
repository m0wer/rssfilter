from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class User(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
