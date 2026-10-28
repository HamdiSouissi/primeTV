"""Fournisseurs IPTV (autorisés par l'utilisateur) et playlists importées."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDMixin


class Provider(UUIDMixin, TimestampMixin, Base):
    """Un fournisseur : Xtream Codes, URL M3U, ou fournisseur générique."""

    __tablename__ = "providers"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_provider_user_name"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="m3u", nullable=False)  # m3u | xtream | hls | dash
    base_url: Mapped[str | None] = mapped_column(String(500))
    username: Mapped[str | None] = mapped_column(String(255))
    password: Mapped[str | None] = mapped_column(String(255))  # chiffré applicatif (Fernet-like) si fourni
    epg_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    extras: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="providers")  # noqa: F821
    playlists: Mapped[list[Playlist]] = relationship(
        back_populates="provider", cascade="all, delete-orphan", lazy="selectin"
    )


class Playlist(UUIDMixin, TimestampMixin, Base):
    """Playlist M3U/M3U8/HLS/DASH importée (URL, fichier ou texte collé)."""

    __tablename__ = "playlists"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider_id: Mapped[str | None] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="url", nullable=False)  # url|file|text|xtream|hls
    url: Mapped[str | None] = mapped_column(String(1000))
    file_name: Mapped[str | None] = mapped_column(String(255))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    channel_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    extras: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    provider: Mapped[Provider | None] = relationship(back_populates="playlists")
    channels: Mapped[list[Channel]] = relationship(  # noqa: F821
        back_populates="playlist", cascade="all, delete-orphan"
    )
