"""Gestion des fournisseurs IPTV autorisés (M3U, Xtream, HLS, DASH)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_provider
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.http import validate_remote_url
from app.db.session import get_db
from app.models.catalog import Channel
from app.models.provider import Playlist, Provider
from app.models.user import User
from app.schemas.common import Message
from app.schemas.provider import ProviderIn, ProviderOut, ProviderUpdate
from app.services.xtream import XtreamError, fetch_xtream, normalize_base_url

router = APIRouter()


def _serialize(db: Session, provider: Provider) -> ProviderOut:
    channel_count = db.scalar(select(func.count(Channel.id)).where(Channel.provider_id == provider.id)) or 0
    playlist_count = db.scalar(select(func.count(Playlist.id)).where(Playlist.provider_id == provider.id)) or 0
    output = ProviderOut.model_validate(provider)
    output.has_password = bool(provider.password)
    output.channel_count = channel_count
    output.playlist_count = playlist_count
    return output


@router.get("", response_model=list[ProviderOut], summary="Lister mes fournisseurs")
def list_providers(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ProviderOut]:
    providers = db.scalars(
        select(Provider).where(Provider.user_id == user.id).order_by(Provider.created_at.desc())
    ).all()
    return [_serialize(db, provider) for provider in providers]


@router.post("", response_model=ProviderOut, status_code=201, summary="Ajouter un fournisseur")
def create_provider(
    payload: ProviderIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProviderOut:
    if payload.kind == "xtream" and not (payload.base_url and payload.username and payload.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "URL, identifiant et mot de passe Xtream requis")
    provider = Provider(
        user_id=user.id,
        name=payload.name,
        kind=payload.kind,
        base_url=payload.base_url,
        username=payload.username,
        password=encrypt_secret(payload.password),
        epg_url=payload.epg_url,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return _serialize(db, provider)


@router.get("/{provider_id}", response_model=ProviderOut, summary="Détail d'un fournisseur")
def get_provider(
    provider_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProviderOut:
    return _serialize(db, get_owned_provider(provider_id, user, db))


@router.patch("/{provider_id}", response_model=ProviderOut, summary="Modifier un fournisseur")
def update_provider(
    provider_id: str,
    payload: ProviderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProviderOut:
    provider = get_owned_provider(provider_id, user, db)
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        provider.password = encrypt_secret(data.pop("password"))
    for attribute, value in data.items():
        setattr(provider, attribute, value)
    db.commit()
    db.refresh(provider)
    return _serialize(db, provider)


@router.delete("/{provider_id}", response_model=Message, summary="Supprimer un fournisseur")
def delete_provider(
    provider_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    provider = get_owned_provider(provider_id, user, db)
    db.delete(provider)
    db.commit()
    return Message(message="Fournisseur supprimé (les chaînes associées sont supprimées)")


@router.post("/{provider_id}/test", response_model=dict, summary="Tester la connexion au fournisseur")
def test_provider(
    provider_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    provider = get_owned_provider(provider_id, user, db)
    if provider.kind != "xtream" or not provider.base_url:
        return {"ok": True, "message": "Fournisseur M3U/HLS : utilisez « Synchroniser » pour tester le flux."}
    try:
        result = fetch_xtream(
            provider.base_url, provider.username or "", decrypt_secret(provider.password) or ""
        )
    except XtreamError as exc:
        return {"ok": False, "message": str(exc)}
    return {
        "ok": True,
        "message": f"{len(result.channels)} chaînes disponibles",
        "server_info": result.server_info,
        "bouquets": result.bouquets[:50],
    }


@router.post("/xtream/preview", response_model=dict, summary="Vérifier des identifiants Xtream avant import")
def preview_xtream(
    base_url: str, username: str, password: str, user: User = Depends(get_current_user)
) -> dict:
    validate_remote_url(normalize_base_url(base_url))
    try:
        result = fetch_xtream(base_url, username, password)
    except XtreamError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {
        "channels": len(result.channels),
        "bouquets": result.bouquets[:30],
        "server_info": result.server_info,
        "epg_urls": result.epg_urls,
        "sample": [channel.name for channel in result.channels[:20]],
    }
