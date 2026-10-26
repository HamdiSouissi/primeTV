"""Import en base : playlists M3U, catalogues Xtream et EPG XMLTV."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.activity import ActivityLog
from app.models.catalog import Bouquet, Category, Channel, Language
from app.models.epg import EpgProgramme, EpgSource
from app.models.provider import Playlist
from app.models.user import User
from app.services.classifier import classify, seed_reference_data
from app.services.m3u import ParsedChannel, ParsedPlaylist
from app.services.streams import StreamAnalysis, merge_hint
from app.services.xmltv import ParsedEpg, parse_xmltv

logger = get_logger(__name__)


@dataclass
class ImportResult:
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    radios: int = 0
    encrypted: int = 0
    categories: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    epg_urls: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "radios": self.radios,
            "encrypted": self.encrypted,
            "categories": self.categories,
            "warnings": self.warnings,
            "epg_urls": self.epg_urls,
        }


def as_utc(value: datetime | None) -> datetime | None:
    """Normalise un datetime (SQLite renvoie parfois des valeurs naïves)."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@dataclass
class EpgImportResult:
    channels: int = 0
    programmes: int = 0
    matched_channels: int = 0
    replaced: bool = False
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "channels": self.channels,
            "programmes": self.programmes,
            "matched_channels": self.matched_channels,
            "replaced": self.replaced,
            "warnings": self.warnings,
        }


def stream_key(url: str) -> str:
    """Clé d'unicité d'un flux (sha256 tronqué)."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:40]


def ensure_reference_data(db: Session) -> dict[str, Category]:
    """Insère si besoin les catégories / langues de référence (idempotent)."""
    categories, languages = seed_reference_data()
    existing_categories = {category.slug: category for category in db.scalars(select(Category))}
    for payload in categories:
        if payload["slug"] not in existing_categories:
            category = Category(**payload)
            db.add(category)
            existing_categories[payload["slug"]] = category
    existing_languages = {language.code: language for language in db.scalars(select(Language))}
    for payload in languages:
        if payload["code"] not in existing_languages:
            language = Language(**payload)
            db.add(language)
            existing_languages[payload["code"]] = language
    db.flush()
    return existing_categories


def _bouquet_names(parsed: ParsedChannel, provider_name: str | None) -> list[str]:
    """Bouquets = groupe d'origine (ex. « Sport | Arabic ») + nom du fournisseur."""
    names: list[str] = []
    if parsed.group:
        names.append(parsed.group.strip())
    if provider_name:
        names.append(provider_name)
    deduped: list[str] = []
    for name in names:
        if name and name.lower() not in {existing.lower() for existing in deduped} and len(name) <= 120:
            deduped.append(name)
    return deduped


def _get_or_create_bouquet(db: Session, cache: dict[str, Bouquet], name: str, provider_id: str | None) -> Bouquet:
    cache_key = f"{name.lower()}::{provider_id}"
    if cache_key in cache:
        return cache[cache_key]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:120] or "bouquet"
    existing = db.scalars(select(Bouquet).where(Bouquet.name == name, Bouquet.provider_id == provider_id)).first()
    if existing:
        cache[cache_key] = existing
        return existing
    bouquet = Bouquet(name=name, slug=slug, provider_id=provider_id)
    db.add(bouquet)
    db.flush()
    cache[cache_key] = bouquet
    return bouquet


def import_playlist_content(
    db: Session,
    *,
    playlist: Playlist,
    parsed: ParsedPlaylist,
    provider_name: str | None = None,
    replace: bool = False,
    analysis: StreamAnalysis | None = None,
) -> ImportResult:
    """Insère / met à jour les chaînes d'une playlist parsée.

    * ``replace=True`` : supprime les chaînes absentes du nouveau contenu ;
    * les chaînes existantes sont mises à jour (nom, logo, catégorie, chiffrement) ;
    * les favoris et l'historique sont conservés (clé stable sur l'URL du flux).
    """
    ensure_reference_data(db)
    categories = {category.slug: category for category in db.scalars(select(Category))}
    languages = {language.code: language for language in db.scalars(select(Language))}
    bouquets_cache: dict[str, Bouquet] = {}

    result = ImportResult(epg_urls=list(parsed.epg_urls))
    channels = parsed.channels[: settings.MAX_IMPORT_CHANNELS]
    if len(parsed.channels) > len(channels):
        result.warnings.append(
            f"Seules les {settings.MAX_IMPORT_CHANNELS} premières chaînes ont été importées"
        )
    result.total = len(channels)

    existing_by_key = {
        channel.stream_key: channel
        for channel in db.scalars(select(Channel).where(Channel.playlist_id == playlist.id))
    }
    seen_keys: set[str] = set()

    for index, parsed_channel in enumerate(channels):
        key = stream_key(parsed_channel.url)
        seen_keys.add(key)
        classification = classify(
            parsed_channel.name,
            group=parsed_channel.group,
            tvg_language=parsed_channel.tvg_language,
            country=parsed_channel.tvg_country,
            is_radio_hint=parsed_channel.is_radio,
            has_epg=bool(parsed_channel.tvg_id),
            encrypted_hint=bool(parsed_channel.encryption_hint),
        )
        channel_analysis = analysis if analysis and parsed.kind != "m3u" else None
        if parsed_channel.encryption_hint:
            channel_analysis = merge_hint(channel_analysis or StreamAnalysis(), parsed_channel.encryption_hint)

        encrypted = bool(channel_analysis and channel_analysis.is_encrypted) or bool(parsed_channel.encryption_hint)
        encryption = channel_analysis.encryption if channel_analysis else "unknown"
        if not encrypted and not channel_analysis:
            encryption = "unknown"

        dataset = {
            "name": parsed_channel.name,
            "normalized_name": classification.normalized_name,
            "tvg_id": parsed_channel.tvg_id,
            "epg_channel_id": parsed_channel.tvg_id,
            "logo": parsed_channel.logo,
            "stream_url": parsed_channel.url,
            "stream_type": parsed_channel.stream_type,
            "group_title": parsed_channel.group,
            "country": (parsed_channel.tvg_country or "")[:8] or None,
            "quality": classification.quality,
            "is_radio": parsed_channel.is_radio,
            "is_encrypted": encrypted,
            "encryption": encryption,
            "drm_systems": channel_analysis.drm_systems if channel_analysis else [],
            "priority": classification.priority,
            "sort_index": index,
            "category_id": categories[classification.category_slug].id
            if classification.category_slug in categories
            else None,
            "language_id": languages[classification.language_code].id
            if classification.language_code in languages
            else None,
            "extras": {
                **parsed_channel.extras,
                "tags": classification.tags,
                "duration": parsed_channel.duration,
                "variants": channel_analysis.as_dict()["variants"] if channel_analysis else [],
                "subtitles": channel_analysis.subtitles if channel_analysis else [],
            },
            "is_active": True,
        }

        existing = existing_by_key.get(key)
        if existing:
            for attribute, value in dataset.items():
                if attribute in {"is_encrypted", "encryption"} and not encrypted:
                    continue
                setattr(existing, attribute, value)
            channel = existing
            result.updated += 1
        else:
            channel = Channel(
                playlist_id=playlist.id,
                provider_id=playlist.provider_id,
                stream_key=key,
                status="unknown",
                **dataset,
            )
            db.add(channel)
            existing_by_key[key] = channel
            result.created += 1

        # Bouquets issus du group-title et du fournisseur
        bouquet_objs = [
            _get_or_create_bouquet(db, bouquets_cache, name, playlist.provider_id)
            for name in _bouquet_names(parsed_channel, provider_name)
        ]
        if bouquet_objs:
            channel.bouquets = bouquet_objs

        if parsed_channel.is_radio:
            result.radios += 1
        if encrypted:
            result.encrypted += 1
        result.categories[classification.category_slug] = result.categories.get(classification.category_slug, 0) + 1

        if index and index % 500 == 0:
            db.flush()

    if replace:
        for key, channel in existing_by_key.items():
            if key not in seen_keys:
                db.delete(channel)
                result.skipped += 1

    playlist.channel_count = len(channels)
    playlist.last_sync_at = datetime.now(UTC)
    playlist.last_error = None
    playlist.content_hash = hashlib.sha256(
        "|".join(parsed_channel.url for parsed_channel in channels).encode("utf-8")
    ).hexdigest()

    db.add(
        ActivityLog(
            user_id=playlist.user_id,
            action="playlist.import",
            message=f"Import de « {playlist.name} » : {result.created} ajoutées, {result.updated} mises à jour",
            context=result.as_dict(),
        )
    )
    db.commit()
    logger.info("Import playlist %s : %s", playlist.name, result.as_dict())
    return result


def save_epg_urls(db: Session, user: User, urls: list[str], provider_id: str | None = None) -> list[EpgSource]:
    """Crée (si besoin) les sources EPG déclarées par une playlist."""
    created: list[EpgSource] = []
    for url in urls:
        existing = db.scalars(
            select(EpgSource).where(EpgSource.user_id == user.id, EpgSource.url == url)
        ).first()
        if existing:
            created.append(existing)
            continue
        name = url.rstrip("/").split("/")[-1] or "EPG"
        source = EpgSource(user_id=user.id, provider_id=provider_id, name=f"EPG {name}", url=url, status="pending")
        db.add(source)
        created.append(source)
    db.commit()
    return created


def import_xmltv_content(
    db: Session, *, source: EpgSource, content: str, replace: bool = True
) -> EpgImportResult:
    """Importe un document XMLTV dans une source EPG et associe les chaînes."""
    parsed: ParsedEpg = parse_xmltv(content)
    result = EpgImportResult(
        channels=len(parsed.channels),
        programmes=len(parsed.programmes),
        replaced=replace,
        warnings=parsed.warnings,
    )

    if replace:
        db.query(EpgProgramme).filter(EpgProgramme.source_id == source.id).delete(synchronize_session=False)
        db.flush()

    # Association xmltv_id -> channel_id
    channel_rows = db.execute(
        select(Channel.id, Channel.epg_channel_id, Channel.tvg_id, Channel.normalized_name)
    ).all()
    by_xmltv: dict[str, str] = {}
    by_name: dict[str, str] = {}
    for channel_id, epg_channel_id, tvg_id, normalized_name in channel_rows:
        if epg_channel_id:
            by_xmltv.setdefault(epg_channel_id.lower(), channel_id)
        if tvg_id:
            by_xmltv.setdefault(tvg_id.lower(), channel_id)
        if normalized_name:
            by_name.setdefault(normalized_name, channel_id)

    display_names: dict[str, str] = {}
    for xmltv_id, meta in parsed.channels.items():
        if meta.get("name"):
            display_names[meta["name"].lower()] = xmltv_id

    matched_channel_ids: set[str] = set()
    batch: list[EpgProgramme] = []
    for programme in parsed.programmes:
        channel_id = by_xmltv.get(programme.xmltv_id.lower())
        if channel_id is None:
            xmltv_id = display_names.get(programme.xmltv_id.lower())
            if xmltv_id:
                channel_id = by_xmltv.get(xmltv_id.lower())
        if channel_id:
            matched_channel_ids.add(channel_id)
        batch.append(
            EpgProgramme(
                source_id=source.id,
                channel_id=channel_id,
                xmltv_id=programme.xmltv_id,
                title=programme.title,
                subtitle=programme.subtitle,
                description=programme.description,
                category=programme.category,
                icon=programme.icon,
                rating=programme.rating,
                start_at=programme.start_at,
                stop_at=programme.stop_at,
            )
        )
        if len(batch) >= 1000:
            db.bulk_save_objects(batch)
            db.flush()
            batch.clear()
    if batch:
        db.bulk_save_objects(batch)
        db.flush()

    # Lier les chaînes sans EPG mais dont le nom correspond à un display-name XMLTV
    unmatched = db.scalars(select(Channel).where(Channel.epg_channel_id.is_(None))).all()
    linked = 0
    for channel in unmatched:
        xmltv_id = display_names.get(channel.normalized_name)
        if xmltv_id:
            channel.epg_channel_id = xmltv_id
            linked += 1
    result.matched_channels = len(matched_channel_ids) + linked

    source.programme_count = len(parsed.programmes)
    source.last_sync_at = datetime.now(UTC)
    source.status = "success"
    source.last_error = None
    db.add(
        ActivityLog(
            user_id=source.user_id,
            action="epg.import",
            message=f"EPG « {source.name} » : {len(parsed.programmes)} programmes, {result.matched_channels} chaînes associées",
            context=result.as_dict(),
        )
    )
    db.commit()
    return result
