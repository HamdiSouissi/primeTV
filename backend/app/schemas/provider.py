from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="m3u", pattern="^(m3u|xtream|hls|dash)$")
    base_url: str | None = Field(default=None, max_length=500)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=255)
    epg_url: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    is_active: bool = True

    @field_validator("base_url")
    @classmethod
    def _url_scheme(cls, value: str | None) -> str | None:
        if value and not value.startswith(("http://", "https://")):
            value = f"http://{value}"
        return value


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = Field(default=None, pattern="^(m3u|xtream|hls|dash)$")
    base_url: str | None = None
    username: str | None = None
    password: str | None = None
    epg_url: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ProviderOut(ORMModel):
    id: str
    name: str
    kind: str
    base_url: str | None = None
    username: str | None = None
    has_password: bool = False
    epg_url: str | None = None
    notes: str | None = None
    is_active: bool
    channel_count: int = 0
    playlist_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlaylistIn(BaseModel):
    """Import d'une playlist : par URL, fichier (multipart) ou texte brut."""

    name: str | None = Field(default=None, max_length=180)
    provider_id: str | None = None
    source_type: str = Field(default="url", pattern="^(url|text|xtream|hls|dash)$")
    url: str | None = Field(default=None, max_length=1000)
    content: str | None = Field(default=None, description="Contenu M3U collé (source_type=text)")
    epg_url: str | None = Field(default=None, max_length=1000)
    replace: bool = True
    probe: bool = False

    @field_validator("url")
    @classmethod
    def _url_format(cls, value: str | None) -> str | None:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("URL http(s) attendue")
        return value


class XtreamImportIn(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    base_url: str = Field(description="URL du portail, ex. http://host:8080")
    username: str
    password: str
    epg: bool = True
    probe: bool = False


class PlaylistOut(ORMModel):
    id: str
    name: str
    source_type: str
    url: str | None = None
    file_name: str | None = None
    provider_id: str | None = None
    channel_count: int
    is_active: bool
    auto_sync: bool
    last_sync_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ImportResultOut(BaseModel):
    playlist: PlaylistOut | None = None
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    radios: int = 0
    encrypted: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    epg_urls: list[str] = Field(default_factory=list)
    epg_sources: list[str] = Field(default_factory=list)


class PlaylistUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    is_active: bool | None = None
    auto_sync: bool | None = None
