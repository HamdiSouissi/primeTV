from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class EpgSourceIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    url: str | None = Field(default=None, max_length=1000)
    provider_id: str | None = None


class EpgSourceOut(ORMModel):
    id: str
    name: str
    url: str | None = None
    file_name: str | None = None
    provider_id: str | None = None
    programme_count: int
    status: str
    last_error: str | None = None
    last_sync_at: datetime | None = None
    created_at: datetime | None = None


class EpgProgrammeOut(ORMModel):
    id: str
    xmltv_id: str
    channel_id: str | None = None
    title: str
    subtitle: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    start_at: datetime
    stop_at: datetime


class EpgImportResultOut(BaseModel):
    source: EpgSourceOut | None = None
    channels: int = 0
    programmes: int = 0
    matched_channels: int = 0
    warnings: list[str] = Field(default_factory=list)
