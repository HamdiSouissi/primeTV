"""Favoris par profil (création, suppression, synchronisation)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_active_profile, get_current_user
from app.db.session import get_db
from app.models.activity import Favorite
from app.models.catalog import Channel
from app.models.user import Profile, User
from app.schemas.activity import FavoriteIn, FavoriteOut
from app.schemas.common import Message

router = APIRouter()


@router.get("", response_model=list[FavoriteOut], summary="Lister mes favoris")
def list_favorites(
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> list[FavoriteOut]:
    rows = db.scalars(
        select(Favorite)
        .where(Favorite.profile_id == profile.id)
        .order_by(Favorite.position, Favorite.created_at.desc())
    ).unique().all()
    return [FavoriteOut.model_validate(row) for row in rows]


@router.post("", response_model=FavoriteOut, status_code=201, summary="Ajouter un favori")
def add_favorite(
    payload: FavoriteIn,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> FavoriteOut:
    channel = db.get(Channel, payload.channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    existing = db.scalars(
        select(Favorite).where(
            Favorite.profile_id == profile.id, Favorite.channel_id == payload.channel_id
        )
    ).first()
    if existing:
        return FavoriteOut.model_validate(existing)
    favorite = Favorite(user_id=user.id, profile_id=profile.id, channel_id=payload.channel_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return FavoriteOut.model_validate(favorite)


@router.delete("/{channel_id}", response_model=Message, summary="Retirer un favori")
def remove_favorite(
    channel_id: str,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> Message:
    favorite = db.scalars(
        select(Favorite).where(Favorite.profile_id == profile.id, Favorite.channel_id == channel_id)
    ).first()
    if not favorite:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Favori introuvable")
    db.delete(favorite)
    db.commit()
    return Message(message="Favori retiré")


@router.put("/sync", response_model=list[FavoriteOut], summary="Synchroniser une liste de favoris")
def sync_favorites(
    payload: list[FavoriteIn],
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> list[FavoriteOut]:
    """Remplace les favoris du profil actif (utile pour la synchronisation multi-appareils)."""
    wanted_ids = [item.channel_id for item in payload]
    valid_ids = set(
        db.scalars(select(Channel.id).where(Channel.id.in_(wanted_ids or ["-"]))).all()
    )
    existing = {
        favorite.channel_id: favorite
        for favorite in db.scalars(select(Favorite).where(Favorite.profile_id == profile.id))
    }
    for channel_id, favorite in list(existing.items()):
        if channel_id not in valid_ids:
            db.delete(favorite)
    for position, channel_id in enumerate(wanted_ids):
        if channel_id not in valid_ids:
            continue
        if channel_id in existing:
            existing[channel_id].position = position
        else:
            db.add(
                Favorite(user_id=user.id, profile_id=profile.id, channel_id=channel_id, position=position)
            )
    db.commit()
    return list_favorites(user=user, profile=profile, db=db)
