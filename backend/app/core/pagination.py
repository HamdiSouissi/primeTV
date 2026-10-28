"""Pagination réutilisable + enveloppe de réponse standard."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(24, ge=1, le=200)
    sort: str | None = None
    order: str = "desc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1, description="Numéro de page (1-indexé)"),
    page_size: int = Query(24, ge=1, le=200, description="Éléments par page"),
    sort: str | None = Query(None, description="Champ de tri"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size, sort=sort, order=order)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def build_page(items: Sequence[T], total: int, params: PageParams) -> Page[T]:
    return Page[T](
        items=list(items),
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=math.ceil(total / params.page_size) if params.page_size else 0,
    )


@dataclass
class PaginatedResult(Generic[T]):
    items: list[T]
    total: int
