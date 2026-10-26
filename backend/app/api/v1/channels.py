"""Chaînes : recherche, filtres, détail, lecture et clés de déchiffrement."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_active_profile, get_current_user
from app.core.cache import cache
from app.core.pagination import Page, PageParams, page_params
from app.db.session import get_db
from app.models.activity import Favorite
from app.models.catalog import Bouquet, Category, Channel, Language, channel_bouquets
from app.models.epg import EpgProgramme
from app.models.user import Profile, User
from app.schemas.catalog import (
    ChannelDetail,
    ChannelUpdate,
    ClearKeyIn,
    NowNextOut,
    PlaybackOut,
    VariantOut,
)
from app.schemas.common import Message
from app.services.classifier import normalize_text
from app.services.importer import as_utc
from app.services.proxy import proxy_url
from app.services.scanner import apply_probe, probe_stream

router = APIRouter()

_SORTABLE = {
    "priority": Channel.priority,
    "name": Channel.name,
    "created_at": Channel.created_at,
    "updated_at": Channel.updated_at,
    "quality": Channel.quality,
    "status": Channel.status,
    "last_checked_at": Channel.last_checked_at,
}


def _favorite_ids(db: Session, profile_id: str) -> set[str]:
    return set(db.scalars(select(Favorite.channel_id).where(Favorite.profile_id == profile_id)))


def _to_detail(channel: Channel, favorites: set[str]) -> ChannelDetail:
    detail = ChannelDetail.model_validate(channel)
    detail.is_favorite = channel.id in favorites
    return detail


@router.get("", response_model=Page[ChannelDetail], summary="Rechercher / lister les chaînes")
def list_channels(
    q: str | None = Query(None, description="Recherche plein texte (nom, groupe, TVG)"),
    category: str | None = Query(None, description="Slug de catégorie (sport, news...)"),
    language: str | None = Query(None, description="Code langue (ar, fr, en, tr, es...)"),
    bouquet: str | None = Query(None, description="Nom ou identifiant de bouquet"),
    provider: str | None = Query(None, description="Identifiant de fournisseur"),
    playlist: str | None = Query(None, description="Identifiant de playlist"),
    stream_type: str | None = Query(None, description="hls | dash | mp4 | mpegts | audio"),
    status_filter: str | None = Query(None, alias="status", description="active | offline | encrypted | unknown"),
    encrypted: bool | None = Query(None),
    radio: bool | None = Query(None),
    favorites_only: bool = Query(False),
    params: PageParams = Depends(page_params),
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> Page[ChannelDetail]:
    """Liste paginée avec tri par défaut « sport & arabe d'abord »."""
    query = select(Channel).where(Channel.is_active.is_(True))
    if q:
        needle = f"%{normalize_text(q)}%"
        raw = f"%{q.strip()}%"
        query = query.where(
            or_(
                Channel.normalized_name.ilike(needle),
                Channel.name.ilike(raw),
                Channel.group_title.ilike(raw),
                Channel.tvg_id.ilike(raw),
            )
        )
    if category:
        query = query.join(Category, Channel.category_id == Category.id, isouter=True).where(
            or_(Category.slug == category, Category.id == category)
        )
    if language:
        query = query.join(Language, Channel.language_id == Language.id, isouter=True).where(
            or_(Language.code == language, Language.id == language)
        )
    if bouquet:
        query = (
            query.join(channel_bouquets, channel_bouquets.c.channel_id == Channel.id)
            .join(Bouquet, Bouquet.id == channel_bouquets.c.bouquet_id)
            .where(or_(Bouquet.id == bouquet, Bouquet.slug == bouquet, Bouquet.name.ilike(f"%{bouquet}%")))
        )
    if provider:
        query = query.where(Channel.provider_id == provider)
    if playlist:
        query = query.where(Channel.playlist_id == playlist)
    if stream_type:
        query = query.where(Channel.stream_type == stream_type)
    if status_filter:
        query = query.where(Channel.status == status_filter)
    if encrypted is not None:
        query = query.where(Channel.is_encrypted.is_(encrypted))
    if radio is not None:
        query = query.where(Channel.is_radio.is_(radio))

    favorites = _favorite_ids(db, profile.id)
    if favorites_only:
        query = query.where(Channel.id.in_(favorites or ["-"]))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    sort_column = _SORTABLE.get(params.sort or "", None)
    if sort_column is not None and params.sort != "priority":
        query = query.order_by(sort_column.desc() if params.order == "desc" else sort_column.asc(), Channel.name)
    else:
        # Les chaînes sportives et arabes remontent naturellement (score de priorité)
        query = query.order_by(Channel.priority.desc(), Channel.name.asc())

    rows = db.scalars(query.offset(params.offset).limit(params.page_size)).unique().all()
    items = [_to_detail(channel, favorites) for channel in rows]
    return Page[ChannelDetail](
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=(total + params.page_size - 1) // params.page_size if params.page_size else 0,
    )


@router.get("/ids", response_model=list[dict], summary="Identifiants légers (cache hors-ligne)")
def channel_ids(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.execute(
        select(Channel.id, Channel.name, Channel.logo, Channel.stream_type, Channel.priority)
        .where(Channel.is_active.is_(True))
        .order_by(Channel.priority.desc(), Channel.name)
    ).all()
    return [
        {"id": row.id, "name": row.name, "logo": row.logo, "stream_type": row.stream_type, "priority": row.priority}
        for row in rows
    ]


@router.get("/{channel_id}", response_model=ChannelDetail, summary="Détail d'une chaîne")
def get_channel(
    channel_id: str,
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> ChannelDetail:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    return _to_detail(channel, _favorite_ids(db, profile.id))


@router.patch("/{channel_id}", response_model=ChannelDetail, summary="Modifier une chaîne")
def update_channel(
    channel_id: str,
    payload: ChannelUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChannelDetail:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    data = payload.model_dump(exclude_unset=True)
    if category_slug := data.pop("category_slug", None):
        category = db.scalars(select(Category).where(Category.slug == category_slug)).first()
        if not category:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Catégorie inconnue")
        channel.category_id = category.id
    if language_code := data.pop("language_code", None):
        language = db.scalars(select(Language).where(Language.code == language_code)).first()
        if not language:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Langue inconnue")
        channel.language_id = language.id
    for attribute, value in data.items():
        setattr(channel, attribute, value)
    if data.get("name"):
        channel.normalized_name = normalize_text(data["name"])
    db.commit()
    db.refresh(channel)
    cache.invalidate_prefix("channels:")
    return _to_detail(channel, set())


@router.delete("/{channel_id}", response_model=Message, summary="Supprimer une chaîne")
def delete_channel(channel_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Message:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    db.delete(channel)
    db.commit()
    cache.invalidate_prefix("channels:")
    return Message(message="Chaîne supprimée")


@router.post("/{channel_id}/refresh", response_model=dict, summary="Tester un flux et actualiser son état")
def refresh_channel(
    channel_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    outcome = probe_stream(channel.id, channel.stream_url, channel.stream_type)
    apply_probe(db, channel, outcome)
    db.commit()
    db.refresh(channel)
    return {
        "status": channel.status,
        "http_status": channel.http_status,
        "encryption": channel.encryption,
        "is_encrypted": channel.is_encrypted,
        "variants": [VariantOut(**variant).model_dump() for variant in (channel.extras or {}).get("variants", [])],
    }


@router.get("/{channel_id}/play", response_model=PlaybackOut, summary="Obtenir l'URL de lecture")
def play_channel(
    channel_id: str,
    proxy: bool = Query(True, description="Passer par le proxy HLS (CORS/déchiffrement côté client)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaybackOut:
    """Retourne tout ce qu'il faut au lecteur : URL, type, variantes, DRM et clés."""
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    extras = channel.extras or {}
    variants = [VariantOut(**variant) for variant in extras.get("variants", []) if isinstance(variant, dict)]
    clear_keys: dict = channel.clear_keys or {}
    clearkey_license = None
    key_system = None
    if clear_keys:
        key_system = "clearkey"
        clearkey_license = {
            "keys": [{"kty": "oct", "kid": kid, "k": key} for kid, key in clear_keys.items()],
            "type": "temporary",
        }
    needs_proxy = proxy and channel.stream_type in {"hls", "dash"}
    message = None
    if channel.is_encrypted and not clear_keys:
        if channel.drm_systems:
            message = (
                "Flux protégé par DRM (Widevine/PlayReady). Lecture non prise en charge : "
                "utilisez une source libre ou votre propre lecteur agréé."
            )
        else:
            message = "Flux chiffré (AES-128/ClearKey). Ajoutez vos clés dans « Accès » si vous en disposez."
    return PlaybackOut(
        channel_id=channel.id,
        url=proxy_url(channel.stream_url, channel.id) if needs_proxy else channel.stream_url,
        direct_url=channel.stream_url,
        stream_type=channel.stream_type,
        is_encrypted=channel.is_encrypted,
        encryption=channel.encryption,
        drm_systems=channel.drm_systems or [],
        variants=variants,
        subtitles=extras.get("subtitles", []),
        audio_tracks=extras.get("audio_tracks", []),
        has_keys=bool(clear_keys),
        key_system=key_system,
        clearkey_license=clearkey_license,
        message=message,
    )


@router.put("/{channel_id}/keys", response_model=Message, summary="Enregistrer une clé ClearKey/AES-128")
def set_channel_key(
    channel_id: str,
    payload: ClearKeyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    """Enregistre une clé que vous êtes en droit d'utiliser (contenu libre, abonnement).

    PrimeTV ne fournit ni ne contourne aucune clé : cette fonction sert uniquement à
    transmettre au lecteur une clé légitimement détenue par l'utilisateur.
    """
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    keys = dict(channel.clear_keys or {})
    keys[payload.kid] = payload.key
    channel.clear_keys = keys
    if not channel.is_encrypted:
        channel.is_encrypted = True
        channel.encryption = "clearkey"
    db.commit()
    return Message(message="Clé enregistrée", detail=f"{len(keys)} clé(s) disponible(s)")


@router.delete("/{channel_id}/keys/{kid}", response_model=Message, summary="Supprimer une clé")
def delete_channel_key(
    channel_id: str, kid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    keys = dict(channel.clear_keys or {})
    keys.pop(kid.lower(), None)
    channel.clear_keys = keys
    db.commit()
    return Message(message="Clé supprimée")


@router.get("/{channel_id}/epg", response_model=NowNextOut, summary="Programme en cours et suivant")
def channel_epg(
    channel_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> NowNextOut:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chaîne introuvable")
    now = datetime.now(UTC)
    identifiers = [item for item in {channel.epg_channel_id, channel.tvg_id, channel.normalized_name} if item]
    if not identifiers:
        return NowNextOut()
    programme_query = select(EpgProgramme).where(
        or_(EpgProgramme.channel_id == channel.id, EpgProgramme.xmltv_id.in_(identifiers))
    )
    current = db.scalars(
        programme_query.where(EpgProgramme.start_at <= now, EpgProgramme.stop_at > now).order_by(EpgProgramme.start_at)
    ).first()
    upcoming = db.scalars(
        programme_query.where(EpgProgramme.start_at > now).order_by(EpgProgramme.start_at)
    ).first()

    def serialize(programme: EpgProgramme | None) -> dict | None:
        if not programme:
            return None
        return {
            "id": programme.id,
            "title": programme.title,
            "subtitle": programme.subtitle,
            "description": programme.description,
            "category": programme.category,
            "icon": programme.icon,
            "start_at": programme.start_at.isoformat(),
            "stop_at": programme.stop_at.isoformat(),
            "progress": round(
                max(
                    0.0,
                    min(
                        1.0,
                        (now - as_utc(programme.start_at)).total_seconds()
                        / max(1.0, (as_utc(programme.stop_at) - as_utc(programme.start_at)).total_seconds()),
                    ),
                ),
                3,
            ),
        }

    return NowNextOut(current=serialize(current), next=serialize(upcoming))
