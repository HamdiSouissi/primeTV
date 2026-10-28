"""Scan et actualisation automatique du catalogue (chaînes chiffrées incluses)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_playlist
from app.db.session import get_db
from app.models.activity import ScanJob
from app.models.user import User
from app.schemas.activity import ScanJobOut, ScanRequest
from app.services.scanner import run_scan_job

router = APIRouter()


@router.post("", response_model=ScanJobOut, status_code=202, summary="Lancer un scan / rafraîchissement")
def start_scan(
    payload: ScanRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanJobOut:
    """Lance en arrière-plan le test des flux et la détection du chiffrement.

    * ``probe=true`` : teste réellement chaque flux (HTTP + analyse du manifeste HLS/DASH) ;
    * sans ``playlist_id``/``provider_id``/``channel_ids`` : scanne tout le catalogue.
    """
    if payload.playlist_id:
        get_owned_playlist(payload.playlist_id, user, db)
    job = ScanJob(
        user_id=user.id,
        playlist_id=payload.playlist_id,
        provider_id=payload.provider_id,
        probe=payload.probe,
        status="queued",
        logs=["Job en file d'attente"],
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background.add_task(run_scan_job, job.id, payload.channel_ids)
    return ScanJobOut.model_validate(job)


@router.get("/jobs", response_model=list[ScanJobOut], summary="Historique des scans")
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScanJobOut]:
    rows = db.scalars(
        select(ScanJob).where(ScanJob.user_id == user.id).order_by(ScanJob.created_at.desc()).limit(limit)
    ).all()
    return [ScanJobOut.model_validate(row) for row in rows]


@router.get("/jobs/{job_id}", response_model=ScanJobOut, summary="État d'un scan")
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ScanJobOut:
    job = db.get(ScanJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job introuvable")
    return ScanJobOut.model_validate(job)


@router.get("/latest", response_model=ScanJobOut | None, summary="Dernier scan exécuté")
def latest_job(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ScanJobOut | None:
    job = db.scalars(
        select(ScanJob).where(ScanJob.user_id == user.id).order_by(ScanJob.created_at.desc())
    ).first()
    return ScanJobOut.model_validate(job) if job else None
