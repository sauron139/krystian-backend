import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Slug = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=1, max_length=120)
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class MediaOut(ORMModel):
    id: uuid.UUID
    url: str
    content_type: str
    width: int | None
    height: int | None
    alt_text: str


class ReorderIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, description="IDs in their new display order")
