"""Réglages utilisateur (clé/valeur) et préférences d'interface."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.activity import Setting
from app.models.user import User
from app.schemas.activity import SettingIn, SettingOut
from app.schemas.common import Message

router = APIRouter()


@router.get("", response_model=list[SettingOut], summary="Lister mes réglages")
def list_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SettingOut]:
    rows = db.scalars(
        select(Setting).where((Setting.user_id == user.id) | (Setting.user_id.is_(None))).order_by(Setting.key)
    ).all()
    return [SettingOut.model_validate(row) for row in rows]


@router.put("", response_model=SettingOut, summary="Créer / mettre à jour un réglage")
def upsert_setting(
    payload: SettingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SettingOut:
    setting = db.scalars(
        select(Setting).where(Setting.user_id == user.id, Setting.key == payload.key)
    ).first()
    if setting:
        setting.value = payload.value
    else:
        setting = Setting(user_id=user.id, key=payload.key, value=payload.value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return SettingOut.model_validate(setting)


@router.delete("/{key}", response_model=Message, summary="Supprimer un réglage")
def delete_setting(key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Message:
    setting = db.scalars(select(Setting).where(Setting.user_id == user.id, Setting.key == key)).first()
    if not setting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Réglage introuvable")
    db.delete(setting)
    db.commit()
    return Message(message="Réglage supprimé")
