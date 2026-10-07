from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Detail(BaseModel):
    detail: str


class Listing(BaseModel, Generic[T]):
    items: list[T]
