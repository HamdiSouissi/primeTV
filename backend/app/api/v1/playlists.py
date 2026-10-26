"""Import et synchronisation des playlists (URL, fichier, texte, Xtream, HLS/DASH)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_playlist
from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.http import StreamFetchError, fetch_text, validate_remote_url
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.provider import Playlist, Provider
from app.models.user import User
from app.schemas.common import Message
from app.schemas.provider import (
    ImportResultOut,
    PlaylistIn,
    PlaylistOut,
    PlaylistUpdate,
    XtreamImportIn,
)
from app.services.importer import import_playlist_content, save_epg_urls
from app.services.m3u import ParsedPlaylist, parse_hls_master, parse_m3u
from app.services.xtream import XtreamError, fetch_xtream

logger = get_logger(__name__)
router = APIRouter()


def _import(db: Session, user: User, playlist: Playlist, parsed: ParsedPlaylist, provider_name: str | None, replace: bool) -> dict:
    result = import_playlist_content(
        db, playlist=playlist, parsed=parsed, provider_name=provider_name, replace=replace
    )
    sources = save_epg_urls(db, user, parsed.epg_urls, playlist.provider_id) if parsed.epg_urls else []
    db.refresh(playlist)
    payload = result.as_dict()
    payload["playlist"] = PlaylistOut.model_validate(playlist)
    payload["epg_sources"] = [source.id for source in sources]
    return payload


MAX_STORED_CONTENT = 5 * 1024 * 1024


def _extras(parsed: ParsedPlaylist, content: str | None, url: str | None) -> dict:
    """Métadonnées conservées sur la playlist (dont le contenu pour re-scan hors-ligne)."""
    extras: dict = {"warnings": parsed.warnings, "kind": parsed.kind}
    if not url and content and len(content) <= MAX_STORED_CONTENT:
        extras["content"] = content
    return extras


@router.get("", response_model=list[PlaylistOut], summary="Lister mes playlists")
def list_playlists(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PlaylistOut]:
    rows = db.scalars(
        select(Playlist).where(Playlist.user_id == user.id).order_by(Playlist.created_at.desc())
    ).all()
    return [PlaylistOut.model_validate(row) for row in rows]


@router.post("", response_model=ImportResultOut, status_code=201, summary="Importer une playlist (URL ou texte)")
def create_playlist(
    payload: PlaylistIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ImportResultOut:
    """Importe une playlist M3U/M3U8/HLS/DASH depuis une URL ou un contenu collé."""
    provider_name = None
    if payload.provider_id:
        provider = db.get(Provider, payload.provider_id)
        if not provider or provider.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Fournisseur introuvable")
        provider_name = provider.name

    content: str | None = payload.content
    url = payload.url
    source_type = payload.source_type

    if not content and not url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fournir une URL ou un contenu M3U")

    if url and not content:
        validate_remote_url(url)
        try:
            content = fetch_text(url)
        except StreamFetchError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    assert content is not None
    parsed = parse_m3u(content)
    if url and parsed.kind in {"hls_master", "hls_media"}:
        parsed = parse_hls_master(content, url) if parsed.kind == "hls_master" else parsed
        source_type = "hls"
    if parsed.kind == "invalid":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Playlist invalide : " + "; ".join(parsed.warnings or ["format non reconnu"]),
        )
    if not parsed.channels and parsed.kind != "hls_media":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aucune chaîne détectée dans la playlist")

    playlist = Playlist(
        user_id=user.id,
        provider_id=payload.provider_id,
        name=payload.name or (url.split("/")[-1][:180] if url else "Playlist importée"),
        source_type=source_type,
        url=url,
        is_active=True,
        extras=_extras(parsed, content, url),
    )
    db.add(playlist)
    db.flush()
    payload_dict = _import(db, user, playlist, parsed, provider_name, payload.replace)
    return ImportResultOut(**payload_dict)


@router.post("/upload", response_model=ImportResultOut, status_code=201, summary="Importer un fichier M3U")
async def upload_playlist(
    file: UploadFile = File(..., description="Fichier .m3u / .m3u8"),
    name: str | None = Form(None),
    provider_id: str | None = Form(None),
    replace: bool = Form(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImportResultOut:
    raw = await file.read()
    if len(raw) > settings.MAX_PLAYLIST_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Fichier trop volumineux")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("latin-1", errors="replace")

    parsed = parse_m3u(content)
    if not parsed.channels and parsed.kind != "hls_master":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aucune chaîne détectée dans le fichier")
    provider_name = None
    if provider_id:
        provider = db.get(Provider, provider_id)
        if not provider or provider.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Fournisseur introuvable")
        provider_name = provider.name

    playlist = Playlist(
        user_id=user.id,
        provider_id=provider_id,
        name=name or (file.filename or "Playlist importée")[:180],
        source_type="file",
        file_name=file.filename,
        is_active=True,
        extras=_extras(parsed, content, None),
    )
    db.add(playlist)
    db.flush()
    return ImportResultOut(**_import(db, user, playlist, parsed, provider_name, replace))


@router.post("/xtream", response_model=ImportResultOut, status_code=201, summary="Importer un portail Xtream Codes")
def import_xtream(
    payload: XtreamImportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ImportResultOut:
    validate_remote_url(payload.base_url)
    try:
        xtream = fetch_xtream(payload.base_url, payload.username, payload.password)
    except XtreamError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    provider = Provider(
        user_id=user.id,
        name=payload.name or f"Xtream {payload.base_url.split('//')[-1][:60]}",
        kind="xtream",
        base_url=payload.base_url,
        username=payload.username,
        password=encrypt_secret(payload.password),
        epg_url=next(iter(xtream.epg_urls), None),
    )
    db.add(provider)
    db.flush()

    parsed = ParsedPlaylist(
        channels=xtream.channels,
        epg_urls=xtream.epg_urls if payload.epg else [],
        kind="m3u",
        warnings=xtream.warnings,
    )
    playlist = Playlist(
        user_id=user.id,
        provider_id=provider.id,
        name=provider.name,
        source_type="xtream",
        is_active=True,
        auto_sync=True,
    )
    db.add(playlist)
    db.flush()
    return ImportResultOut(**_import(db, user, playlist, parsed, provider.name, True))


@router.post("/{playlist_id}/sync", response_model=ImportResultOut, summary="Synchroniser (actualiser) une playlist")
def sync_playlist(
    playlist_id: str,
    replace: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImportResultOut:
    """Re-télécharge la source et met à jour chaînes, catégories et EPG."""
    playlist = get_owned_playlist(playlist_id, user, db)
    provider = db.get(Provider, playlist.provider_id) if playlist.provider_id else None
    provider_name = provider.name if provider else None

    if playlist.source_type == "xtream" and provider:
        try:
            xtream = fetch_xtream(provider.base_url or "", provider.username or "", decrypt_secret(provider.password) or "")
        except XtreamError as exc:
            playlist.last_error = str(exc)
            db.commit()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        parsed = ParsedPlaylist(channels=xtream.channels, epg_urls=xtream.epg_urls, kind="m3u")
    elif (playlist.extras or {}).get("content"):
        parsed = parse_m3u(playlist.extras["content"])
    elif playlist.url:
        validate_remote_url(playlist.url)
        try:
            content = fetch_text(playlist.url)
        except StreamFetchError as exc:
            playlist.last_error = str(exc)
            db.commit()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        parsed = parse_m3u(content)
        if parsed.kind == "hls_master":
            parsed = parse_hls_master(content, playlist.url)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cette playlist a été importée par fichier : réimportez le fichier pour la mettre à jour.",
        )

    if not parsed.channels:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La source ne contient plus aucune chaîne")
    return ImportResultOut(**_import(db, user, playlist, parsed, provider_name, replace))


@router.patch("/{playlist_id}", response_model=PlaylistOut, summary="Modifier une playlist")
def update_playlist(
    playlist_id: str,
    payload: PlaylistUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaylistOut:
    playlist = get_owned_playlist(playlist_id, user, db)
    for attribute, value in payload.model_dump(exclude_unset=True).items():
        setattr(playlist, attribute, value)
    db.commit()
    db.refresh(playlist)
    return PlaylistOut.model_validate(playlist)


@router.delete("/{playlist_id}", response_model=Message, summary="Supprimer une playlist")
def delete_playlist(
    playlist_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    playlist = get_owned_playlist(playlist_id, user, db)
    db.delete(playlist)
    db.commit()
    return Message(message="Playlist supprimée")
