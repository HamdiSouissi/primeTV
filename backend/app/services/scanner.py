"""Scan / rafraîchissement automatique du catalogue.

Le scan vérifie l'accessibilité des flux, détecte le chiffrement des manifestes HLS/DASH
et met à jour l'état des chaînes. Exécution concurrente bornée pour ne pas saturer le réseau.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.http import get_http_client
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.activity import ActivityLog, ScanJob
from app.models.catalog import Channel
from app.services.streams import StreamAnalysis, analyze_dash, analyze_hls

logger = get_logger(__name__)

_MANIFEST_MAX_BYTES = 512 * 1024


@dataclass
class ProbeOutcome:
    """Résultat réseau d'un flux."""

    channel_id: str
    http_status: int | None
    reachable: bool
    analysis: StreamAnalysis | None
    error: str | None = None


def probe_stream(channel_id: str, url: str, stream_type: str) -> ProbeOutcome:
    """Teste un flux et analyse son manifeste si c'est du HLS/DASH."""
    client = get_http_client()
    try:
        headers = {"Range": "bytes=0-65535"}
        with client.stream("GET", url, headers=headers, timeout=settings.PROBE_TIMEOUT_SECONDS) as response:
            status = response.status_code
            reachable = status < 400
            content_type = response.headers.get("content-type", "")
            analysis: StreamAnalysis | None = None
            looks_manifest = (
                stream_type in {"hls", "dash"}
                or "mpegurl" in content_type.lower()
                or "dash+xml" in content_type.lower()
                or url.lower().endswith((".m3u8", ".mpd"))
            )
            if reachable and looks_manifest:
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > _MANIFEST_MAX_BYTES:
                        break
                    chunks.append(chunk)
                text = b"".join(chunks).decode("utf-8", errors="replace")
                if "#EXTM3U" in text:
                    analysis = analyze_hls(text, base_url=url)
                elif "<MPD" in text or "<mpd" in text:
                    analysis = analyze_dash(text)
            return ProbeOutcome(channel_id, status, reachable, analysis)
    except httpx.HTTPError as exc:
        return ProbeOutcome(channel_id, None, False, None, str(exc)[:200])


def _status_for(outcome: ProbeOutcome, analysis: StreamAnalysis | None) -> str:
    if not outcome.reachable:
        return "offline"
    if analysis and analysis.is_encrypted:
        return "encrypted"
    return "active"


def apply_probe(db: Session, channel: Channel, outcome: ProbeOutcome) -> None:
    """Met à jour une chaîne à partir du résultat de son test réseau."""
    now = datetime.now(UTC)
    channel.http_status = outcome.http_status
    channel.last_checked_at = now
    channel.status = _status_for(outcome, outcome.analysis)
    if outcome.analysis:
        if outcome.analysis.is_encrypted:
            channel.is_encrypted = True
            channel.encryption = outcome.analysis.encryption
            channel.drm_systems = outcome.analysis.drm_systems
        elif channel.encryption in {"unknown", "none"} and not channel.is_encrypted:
            channel.encryption = "none"
        extras = dict(channel.extras or {})
        extras["variants"] = outcome.analysis.as_dict()["variants"]
        extras["subtitles"] = outcome.analysis.subtitles
        extras["audio_tracks"] = outcome.analysis.audio_tracks
        extras["key_uri"] = outcome.analysis.key_uri
        if outcome.analysis.variants:
            heights = []
            for variant in outcome.analysis.variants:
                match = re.search(r"(\d{3,4})x(\d{3,4})", variant.resolution or "")
                if match:
                    heights.append(int(match.group(2)))
            if heights:
                best = max(heights)
                channel.quality = "4K" if best >= 2000 else "FHD" if best >= 1000 else "HD" if best >= 700 else "SD"
        channel.extras = extras


def probe_many(channels: list[Channel]) -> dict[str, ProbeOutcome]:
    """Lance les tests réseau en parallèle (borné par PROBE_CONCURRENCY)."""
    if not channels:
        return {}
    outcomes: dict[str, ProbeOutcome] = {}
    with ThreadPoolExecutor(max_workers=max(1, settings.PROBE_CONCURRENCY)) as pool:
        futures = {
            pool.submit(probe_stream, channel.id, channel.stream_url, channel.stream_type): channel
            for channel in channels
        }
        for future, channel in futures.items():
            try:
                outcomes[channel.id] = future.result()
            except Exception as exc:  # pragma: no cover - défensif
                outcomes[channel.id] = ProbeOutcome(channel.id, None, False, None, str(exc)[:200])
    return outcomes


def run_scan(db: Session, job: ScanJob, channels: list[Channel], *, probe: bool = True) -> ScanJob:
    """Exécute un scan sur une liste de chaînes et met à jour le job."""
    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.total = len(channels)
    job.progress = 0
    job.logs = [f"Scan démarré sur {len(channels)} chaînes (probe={probe})"]
    db.commit()

    try:
        if probe:
            outcomes = probe_many(channels)
        else:
            outcomes = {}
        for index, channel in enumerate(channels, start=1):
            outcome = outcomes.get(channel.id)
            if outcome is not None:
                apply_probe(db, channel, outcome)
                if outcome.reachable:
                    job.active += 1
                else:
                    job.offline += 1
                if channel.is_encrypted:
                    job.encrypted += 1
                    if channel.drm_systems:
                        job.drm_protected += 1
            job.progress = index
            if index % 50 == 0 or index == len(channels):
                db.commit()
            if outcome and outcome.error and len(job.logs) < 200:
                job.logs = [*job.logs, f"{channel.name}: {outcome.error}"]

        job.status = "done"
        job.finished_at = datetime.now(UTC)
        job.progress = job.total
        job.logs = [*job.logs, f"Terminé : {job.active} actives, {job.offline} hors ligne, {job.encrypted} chiffrées"]
        db.add(
            ActivityLog(
                user_id=job.user_id,
                action="scan.finished",
                message=f"Scan terminé : {job.active}/{job.total} flux actifs",
                context={"job_id": job.id, "active": job.active, "offline": job.offline, "encrypted": job.encrypted},
            )
        )
        db.commit()
    except Exception as exc:  # pragma: no cover - dépend du réseau
        db.rollback()
        logger.exception("Scan échoué")
        job = db.get(ScanJob, job.id) or job
        job.status = "failed"
        job.error = str(exc)[:1000]
        job.finished_at = datetime.now(UTC)
        db.commit()
    return job


def run_scan_job(job_id: str, channel_ids: list[str] | None = None) -> None:
    """Point d'entrée d'arrière-plan : ouvre sa propre session."""
    db = SessionLocal()
    try:
        job = db.get(ScanJob, job_id)
        if not job:
            return
        query = select(Channel).where(Channel.is_active.is_(True))
        if channel_ids:
            query = query.where(Channel.id.in_(channel_ids))
        elif job.playlist_id:
            query = query.where(Channel.playlist_id == job.playlist_id)
        elif job.provider_id:
            query = query.where(Channel.provider_id == job.provider_id)
        query = query.order_by(Channel.priority.desc()).limit(settings.SCAN_MAX_CHANNELS)
        channels = list(db.scalars(query))
        run_scan(db, job, channels, probe=job.probe)
    finally:
        db.close()
