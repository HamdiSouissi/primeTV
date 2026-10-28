"""Tableau de bord : compteurs, répartitions et activité récente."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_active_profile, get_current_user
from app.db.session import get_db
from app.models.activity import ActivityLog, Favorite, History, ScanJob
from app.models.catalog import Bouquet, Category, Channel, Language
from app.models.epg import EpgProgramme, EpgSource
from app.models.provider import Playlist, Provider
from app.models.user import Profile, User
from app.schemas.activity import ActivityOut, ScanJobOut, StatsOut

router = APIRouter()


def _count(db: Session, model, *conditions) -> int:
    query = select(func.count()).select_from(model)
    for condition in conditions:
        query = query.where(condition)
    return db.scalar(query) or 0


@router.get("/dashboard", response_model=StatsOut, summary="Statistiques du tableau de bord")
def dashboard(
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> StatsOut:
    by_category = db.execute(
        select(Category.name, Category.slug, Category.color, func.count(Channel.id))
        .join(Channel, Channel.category_id == Category.id)
        .group_by(Category.name, Category.slug, Category.color, Category.position)
        .order_by(Category.position)
    ).all()
    by_language = db.execute(
        select(Language.name, Language.code, Language.flag, func.count(Channel.id))
        .join(Channel, Channel.language_id == Language.id)
        .group_by(Language.name, Language.code, Language.flag, Language.position)
        .order_by(Language.position)
    ).all()
    by_stream_type = db.execute(
        select(Channel.stream_type, func.count(Channel.id)).group_by(Channel.stream_type)
    ).all()
    by_status = db.execute(select(Channel.status, func.count(Channel.id)).group_by(Channel.status)).all()

    recent_activity = db.scalars(
        select(ActivityLog)
        .where((ActivityLog.user_id == user.id) | (ActivityLog.user_id.is_(None)))
        .order_by(ActivityLog.created_at.desc())
        .limit(15)
    ).all()
    history = db.scalars(
        select(History)
        .where(History.profile_id == profile.id)
        .order_by(History.watched_at.desc())
        .limit(10)
    ).unique().all()
    last_scan = db.scalars(
        select(ScanJob).where(ScanJob.user_id == user.id).order_by(ScanJob.created_at.desc())
    ).first()

    return StatsOut(
        channels=_count(db, Channel),
        radios=_count(db, Channel, Channel.is_radio.is_(True)),
        bouquets=_count(db, Bouquet),
        providers=_count(db, Provider),
        playlists=_count(db, Playlist),
        active_streams=_count(db, Channel, Channel.status == "active"),
        offline_streams=_count(db, Channel, Channel.status == "offline"),
        encrypted_streams=_count(db, Channel, Channel.is_encrypted.is_(True)),
        drm_streams=_count(db, Channel, Channel.status == "encrypted"),
        favorites=_count(db, Favorite, Favorite.profile_id == profile.id),
        epg_sources=_count(db, EpgSource),
        epg_programmes=_count(db, EpgProgramme),
        by_category=[
            {"name": name, "slug": slug, "color": color, "count": count}
            for name, slug, color, count in by_category
        ],
        by_language=[
            {"name": name, "code": code, "flag": flag, "count": count}
            for name, code, flag, count in by_language
        ],
        by_stream_type=[{"type": stream_type, "count": count} for stream_type, count in by_stream_type],
        by_status=[{"status": status_name, "count": count} for status_name, count in by_status],
        recent_activity=[ActivityOut.model_validate(entry) for entry in recent_activity],
        history=[
            {
                "id": entry.id,
                "channel_id": entry.channel_id,
                "position_seconds": entry.position_seconds,
                "duration_seconds": entry.duration_seconds,
                "device": entry.device,
                "watched_at": entry.watched_at,
            }
            for entry in history
        ],
        last_scan=ScanJobOut.model_validate(last_scan) if last_scan else None,
    )


@router.get("/activity", response_model=list[ActivityOut], summary="Journal d'activité")
def activity(
    limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ActivityOut]:
    rows = db.scalars(
        select(ActivityLog)
        .where((ActivityLog.user_id == user.id) | (ActivityLog.user_id.is_(None)))
        .order_by(ActivityLog.created_at.desc())
        .limit(min(limit, 200))
    ).all()
    return [ActivityOut.model_validate(row) for row in rows]
