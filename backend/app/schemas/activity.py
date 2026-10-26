from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.catalog import ChannelBase
from app.schemas.common import ORMModel


class FavoriteIn(BaseModel):
    channel_id: str


class FavoriteOut(ORMModel):
    id: str
    channel_id: str
    position: int = 0
    created_at: datetime | None = None
    channel: ChannelBase | None = None


class HistoryIn(BaseModel):
    channel_id: str
    position_seconds: int = Field(default=0, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    device: str | None = Field(default=None, max_length=40)


class HistoryOut(ORMModel):
    id: str
    channel_id: str
    position_seconds: int
    duration_seconds: int | None = None
    device: str | None = None
    watched_at: datetime
    channel: ChannelBase | None = None


class ScanRequest(BaseModel):
    playlist_id: str | None = None
    provider_id: str | None = None
    channel_ids: list[str] | None = Field(default=None, max_length=5000)
    probe: bool = True


class ScanJobOut(ORMModel):
    id: str
    status: str
    progress: int
    total: int
    imported: int
    updated: int
    active: int
    offline: int
    encrypted: int
    drm_protected: int
    probe: bool
    error: str | None = None
    playlist_id: str | None = None
    provider_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    logs: list[str] = Field(default_factory=list)


class SettingIn(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: dict = Field(default_factory=dict)


class SettingOut(ORMModel):
    key: str
    value: dict
    updated_at: datetime | None = None


class ActivityOut(ORMModel):
    id: str
    action: str
    message: str
    level: str
    context: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class StatsOut(BaseModel):
    channels: int = 0
    radios: int = 0
    bouquets: int = 0
    providers: int = 0
    playlists: int = 0
    active_streams: int = 0
    offline_streams: int = 0
    encrypted_streams: int = 0
    drm_streams: int = 0
    favorites: int = 0
    epg_sources: int = 0
    epg_programmes: int = 0
    by_category: list[dict] = Field(default_factory=list)
    by_language: list[dict] = Field(default_factory=list)
    by_stream_type: list[dict] = Field(default_factory=list)
    by_status: list[dict] = Field(default_factory=list)
    recent_activity: list[ActivityOut] = Field(default_factory=list)
    history: list[HistoryOut] = Field(default_factory=list)
    last_scan: ScanJobOut | None = None
