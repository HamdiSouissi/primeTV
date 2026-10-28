"""EPG : sources XMLTV et programmes."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDMixin


class EpgSource(UUIDMixin, TimestampMixin, Base):
    """Source XMLTV importée (URL ou fichier)."""

    __tablename__ = "epg_sources"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000))
    file_name: Mapped[str | None] = mapped_column(String(255))
    last_sync_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    programme_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    extras: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    programmes: Mapped[list[EpgProgramme]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class EpgProgramme(UUIDMixin, TimestampMixin, Base):
    """Un programme EPG (créneau titre/description)."""

    __tablename__ = "epg_programmes"
    __table_args__ = (
        UniqueConstraint("source_id", "xmltv_id", "start_at", name="uq_programme_slot"),
    )

    source_id: Mapped[str] = mapped_column(
        ForeignKey("epg_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel_id: Mapped[str | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True)
    xmltv_id: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80))
    icon: Mapped[str | None] = mapped_column(String(1000))
    rating: Mapped[str | None] = mapped_column(String(16))
    start_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True, nullable=False)
    stop_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True, nullable=False)

    source: Mapped[EpgSource] = relationship(back_populates="programmes")
