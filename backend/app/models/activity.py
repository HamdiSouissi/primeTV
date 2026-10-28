"""Favoris, historique, tâches de scan, réglages et journal d'activité."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDMixin


class Favorite(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("profile_id", "channel_id", name="uq_favorite_profile_channel"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    channel: Mapped[Channel] = relationship(lazy="joined")  # noqa: F821


class History(UUIDMixin, TimestampMixin, Base):
    """Historique de lecture (reprise et statistiques)."""

    __tablename__ = "history"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel_id: Mapped[str] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    device: Mapped[str | None] = mapped_column(String(40))
    watched_at: Mapped[datetime] = mapped_column(
        UTCDateTime, index=True, default=lambda: datetime.now(UTC), nullable=False
    )

    channel: Mapped[Channel] = relationship(lazy="joined")  # noqa: F821


class ScanJob(UUIDMixin, TimestampMixin, Base):
    """Tâche de scan/actualisation exécutée en arrière-plan."""

    __tablename__ = "scan_jobs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), index=True)
    playlist_id: Mapped[str | None] = mapped_column(ForeignKey("playlists.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)  # queued|running|done|failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    offline: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    encrypted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    drm_protected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    probe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    logs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class Setting(UUIDMixin, TimestampMixin, Base):
    """Réglage clé/valeur (global si user_id est NULL)."""

    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_setting_user_key"),)

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ActivityLog(UUIDMixin, TimestampMixin, Base):
    """Journal d'activité (imports, scans, actions admin)."""

    __tablename__ = "activity_logs"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
