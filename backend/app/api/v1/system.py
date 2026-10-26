"""Endpoints système : santé, version, capacités publiques."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import HealthOut

router = APIRouter()
_STARTED_AT = time.time()


@router.get("/healthz", response_model=HealthOut, summary="Sonde de vivacité")
def healthz(db: Session = Depends(get_db)) -> HealthOut:
    database = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover
        database = "error"
    return HealthOut(
        status="ok" if database == "ok" else "degraded",
        version=settings.APP_VERSION,
        environment=settings.ENV,
        database=database,
        cache=cache.backend_name,
        uptime_seconds=round(time.time() - _STARTED_AT, 1),
    )


@router.get("/readyz", summary="Sonde de disponibilité")
def readyz(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/config", summary="Configuration publique (frontend)")
def public_config() -> dict:
    from app.services.classifier import seed_reference_data

    categories, languages = seed_reference_data()
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "allow_registration": settings.ALLOW_REGISTRATION,
        "categories": categories,
        "languages": languages,
        "quality_levels": ["SD", "HD", "FHD", "4K", "8K"],
        "stream_types": ["hls", "dash", "mp4", "mpegts", "audio"],
        "encryption_types": ["none", "aes-128", "clearkey", "sample-aes", "widevine", "playready", "fairplay"],
    }
