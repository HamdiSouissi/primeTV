"""Catalogue : catégories, langues, bouquets et chaînes."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDMixin

# Association N-N chaînes <-> bouquets
channel_bouquets = Table(
    "channel_bouquets",
    Base.metadata,
    Column("channel_id", String(36), ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
    Column("bouquet_id", String(36), ForeignKey("bouquets.id", ondelete="CASCADE"), primary_key=True),
)


class Category(UUIDMixin, TimestampMixin, Base):
    """Catégorie thématique (Sport, News, Movies, Kids, Music, Religion, Documentary...)."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(60))
    color: Mapped[str | None] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    channels: Mapped[list[Channel]] = relationship(back_populates="category")


class Language(UUIDMixin, TimestampMixin, Base):
    """Langue de diffusion."""

    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(60))
    flag: Mapped[str | None] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    channels: Mapped[list[Channel]] = relationship(back_populates="language")


class Bouquet(UUIDMixin, TimestampMixin, Base):
    """Regroupement commercial ou éditorial de chaînes."""

    __tablename__ = "bouquets"
    __table_args__ = (UniqueConstraint("name", "provider_id", name="uq_bouquet_name_provider"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    channels: Mapped[list[Channel]] = relationship(secondary=channel_bouquets, back_populates="bouquets")


class Channel(UUIDMixin, TimestampMixin, Base):
    """Chaîne TV ou station radio avec ses métadonnées de flux."""

    __tablename__ = "channels"
    __table_args__ = (
        UniqueConstraint("playlist_id", "stream_key", name="uq_channel_playlist_stream"),
        Index("ix_channel_priority_name", "priority", "name"),
        Index("ix_channel_filters", "category_id", "language_id", "is_radio"),
    )

    playlist_id: Mapped[str | None] = mapped_column(ForeignKey("playlists.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), index=True)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    language_id: Mapped[str | None] = mapped_column(ForeignKey("languages.id", ondelete="SET NULL"), index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    tvg_id: Mapped[str | None] = mapped_column(String(180), index=True)
    epg_channel_id: Mapped[str | None] = mapped_column(String(180), index=True)
    logo: Mapped[str | None] = mapped_column(String(1000))
    stream_url: Mapped[str] = mapped_column(Text, nullable=False)
    stream_key: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256(url) pour l'unicité
    stream_type: Mapped[str] = mapped_column(String(20), default="hls", nullable=False)  # hls|dash|mp4|mpegts|audio|other
    group_title: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(8), index=True)
    quality: Mapped[str | None] = mapped_column(String(16))  # SD | HD | FHD | 4K
    is_radio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    encryption: Mapped[str] = mapped_column(String(24), default="unknown", nullable=False)
    drm_systems: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Clés ClearKey fournies par l'utilisateur pour du contenu qu'il est en droit de lire.
    clear_keys: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="unknown", index=True, nullable=False)  # active|offline|encrypted|unknown
    http_status: Mapped[int | None] = mapped_column(Integer)
    last_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sort_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extras: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    playlist: Mapped[Playlist | None] = relationship(back_populates="channels")  # noqa: F821
    category: Mapped[Category | None] = relationship(back_populates="channels", lazy="joined")
    language: Mapped[Language | None] = relationship(back_populates="channels", lazy="joined")
    bouquets: Mapped[list[Bouquet]] = relationship(
        secondary=channel_bouquets, back_populates="channels", lazy="selectin"
    )
