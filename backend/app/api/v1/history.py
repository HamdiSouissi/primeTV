"""Historique de lecture et reprise (« continuer la lecture »)."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_active_profile, get_current_user
from app.db.session import get_db
from app.models.activity import History
from app.models.catalog import Channel
from app.models.user import Profile, User
from app.schemas.activity import HistoryIn, HistoryOut
from app.schemas.common import Message

router = APIRouter()


@router.get("", response_model=list[HistoryOut], summary="Historique de lecture")
def list_history(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> list[HistoryOut]:
    rows = db.scalars(
        select(History)
        .where(History.profile_id == profile.id)
        .order_by(History.watched_at.desc())
        .limit(limit)
    ).unique().all()
    return [HistoryOut.model_validate(row) for row in rows]


@router.post("", response_model=HistoryOut, status_code=201, summary="Enregistrer une lecture")
def record_history(
    payload: HistoryIn,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> HistoryOut:
    channel = db.get(Channel, payload.channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    entry = History(
        user_id=user.id,
        profile_id=profile.id,
        channel_id=payload.channel_id,
        position_seconds=payload.position_seconds,
        duration_seconds=payload.duration_seconds,
        device=payload.device,
        watched_at=datetime.now(UTC),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return HistoryOut.model_validate(entry)


@router.get("/continue", response_model=list[HistoryOut], summary="Continuer la lecture")
def continue_watching(
    limit: int = Query(12, ge=1, le=50),
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> list[HistoryOut]:
    rows = db.scalars(
        select(History)
        .where(History.profile_id == profile.id, History.position_seconds > 0)
        .order_by(History.watched_at.desc())
        .limit(limit * 3)
    ).unique().all()
    seen: set[str] = set()
    result: list[HistoryOut] = []
    for row in rows:
        if row.channel_id in seen:
            continue
        seen.add(row.channel_id)
        result.append(HistoryOut.model_validate(row))
        if len(result) >= limit:
            break
    return result


@router.get("/recent", response_model=list[HistoryOut], summary="Dernières chaînes regardées")
def recent_channels(
    limit: int = Query(12, ge=1, le=50),
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> list[HistoryOut]:
    return list_history(limit=limit, user=user, profile=profile, db=db)


@router.delete("/{history_id}", response_model=Message, summary="Supprimer une entrée")
def delete_history(
    history_id: str,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> Message:
    entry = db.get(History, history_id)
    if not entry or entry.profile_id != profile.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entrée introuvable")
    db.delete(entry)
    db.commit()
    return Message(message="Entrée supprimée")


@router.delete("", response_model=Message, summary="Vider l'historique du profil")
def clear_history(
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> Message:
    db.query(History).filter(History.profile_id == profile.id).delete(synchronize_session=False)
    db.commit()
    return Message(message="Historique vidé")
