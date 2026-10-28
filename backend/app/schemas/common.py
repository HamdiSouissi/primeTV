from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str
    detail: str | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class Timestamped(ORMModel):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FacetCount(BaseModel):
    id: str | None = None
    slug: str | None = None
    name: str
    count: int = 0
    color: str | None = None
    icon: str | None = None
    flag: str | None = None
    priority: int = 0


class HealthOut(BaseModel):
    status: str = Field(examples=["ok"])
    version: str
    environment: str
    database: str
    cache: str
    uptime_seconds: float
