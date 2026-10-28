from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class CategoryOut(ORMModel):
    id: str
    name: str
    slug: str
    icon: str | None = None
    color: str | None = None
    position: int = 0


class LanguageOut(ORMModel):
    id: str
    code: str
    name: str
    native_name: str | None = None
    flag: str | None = None
    position: int = 0


class BouquetOut(ORMModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    provider_id: str | None = None
    is_public: bool = True


class ChannelBase(ORMModel):
    id: str
    name: str
    logo: str | None = None
    stream_type: str
    group_title: str | None = None
    country: str | None = None
    quality: str | None = None
    is_radio: bool
    is_encrypted: bool
    encryption: str
    drm_systems: list[str] = Field(default_factory=list)
    status: str
    priority: int = 0
    tvg_id: str | None = None
    epg_channel_id: str | None = None
    category: CategoryOut | None = None
    language: LanguageOut | None = None
    bouquets: list[BouquetOut] = Field(default_factory=list)
    last_checked_at: datetime | None = None
    is_favorite: bool = False


class ChannelDetail(ChannelBase):
    stream_url: str
    provider_id: str | None = None
    playlist_id: str | None = None
    http_status: int | None = None
    extras: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    logo: str | None = None
    category_slug: str | None = None
    language_code: str | None = None
    is_active: bool | None = None
    priority: int | None = None
    tvg_id: str | None = None


class VariantOut(BaseModel):
    label: str
    bandwidth: int = 0
    resolution: str | None = None
    codecs: str | None = None
    url: str | None = None


class PlaybackOut(BaseModel):
    channel_id: str
    url: str
    direct_url: str | None = None
    stream_type: str
    is_encrypted: bool
    encryption: str
    drm_systems: list[str] = Field(default_factory=list)
    variants: list[VariantOut] = Field(default_factory=list)
    subtitles: list[str] = Field(default_factory=list)
    audio_tracks: list[str] = Field(default_factory=list)
    has_keys: bool = False
    key_system: str | None = None
    clearkey_license: dict | None = None
    message: str | None = None


class ClearKeyIn(BaseModel):
    """Clé ClearKey/AES-128 fournie par l'utilisateur (contenu qu'il est en droit de lire)."""

    kid: str = Field(min_length=1, max_length=64, description="Key ID (hex, 32 caractères)")
    key: str = Field(min_length=1, max_length=64, description="Clé (hex, 32 caractères)")

    @field_validator("kid", "key")
    @classmethod
    def _hex_only(cls, value: str) -> str:
        cleaned = value.strip().replace("-", "").lower()
        if not all(char in "0123456789abcdef" for char in cleaned):
            raise ValueError("Valeur hexadécimale attendue")
        return cleaned


class NowNextOut(BaseModel):
    current: dict | None = None
    next: dict | None = None


class ChannelQuery(BaseModel):
    q: str | None = None
    category: str | None = None
    language: str | None = None
    bouquet: str | None = None
    provider: str | None = None
    playlist: str | None = None
    stream_type: str | None = None
    status: str | None = None
    encrypted: bool | None = None
    radio: bool | None = None
    favorites_only: bool = False
    min_quality: str | None = None
