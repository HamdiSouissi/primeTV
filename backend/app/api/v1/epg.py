"""EPG : sources XMLTV, import et programmes."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.http import StreamFetchError, fetch_text, validate_remote_url
from app.db.session import get_db
from app.models.epg import EpgProgramme, EpgSource
from app.models.user import User
from app.schemas.common import Message
from app.schemas.epg import EpgImportResultOut, EpgProgrammeOut, EpgSourceIn, EpgSourceOut
from app.services.importer import import_xmltv_content

router = APIRouter()


def _owned_source(source_id: str, user: User, db: Session) -> EpgSource:
    source = db.get(EpgSource, source_id)
    if not source or source.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source EPG introuvable")
    return source


@router.get("/sources", response_model=list[EpgSourceOut], summary="Lister les sources EPG")
def list_sources(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[EpgSourceOut]:
    rows = db.scalars(
        select(EpgSource).where(EpgSource.user_id == user.id).order_by(EpgSource.created_at.desc())
    ).all()
    return [EpgSourceOut.model_validate(row) for row in rows]


@router.post("/sources", response_model=EpgSourceOut, status_code=201, summary="Ajouter une source EPG")
def create_source(
    payload: EpgSourceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> EpgSourceOut:
    if not payload.url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "URL XMLTV requise")
    validate_remote_url(payload.url)
    source = EpgSource(
        user_id=user.id,
        provider_id=payload.provider_id,
        name=payload.name or payload.url.split("/")[-1][:160] or "EPG",
        url=payload.url,
        status="pending",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return EpgSourceOut.model_validate(source)


@router.post("/sources/{source_id}/sync", response_model=EpgImportResultOut, summary="Synchroniser une source EPG")
def sync_source(
    source_id: str,
    replace: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EpgImportResultOut:
    source = _owned_source(source_id, user, db)
    if not source.url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source sans URL : utilisez l'import de fichier")
    validate_remote_url(source.url)
    try:
        content = fetch_text(source.url, max_bytes=80 * 1024 * 1024)
    except StreamFetchError as exc:
        source.status = "error"
        source.last_error = str(exc)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    try:
        result = import_xmltv_content(db, source=source, content=content, replace=replace)
    except ValueError as exc:
        source.status = "error"
        source.last_error = str(exc)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    db.refresh(source)
    return EpgImportResultOut(source=EpgSourceOut.model_validate(source), **result.as_dict())


@router.post("/upload", response_model=EpgImportResultOut, status_code=201, summary="Importer un fichier XMLTV")
async def upload_xmltv(
    file: UploadFile = File(..., description="Fichier .xml / .xmltv"),
    name: str | None = Form(None),
    replace: bool = Form(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EpgImportResultOut:
    raw = await file.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("latin-1", errors="replace")
    source = EpgSource(
        user_id=user.id,
        name=name or (file.filename or "EPG importé")[:160],
        file_name=file.filename,
        status="pending",
    )
    db.add(source)
    db.flush()
    try:
        result = import_xmltv_content(db, source=source, content=content, replace=replace)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    db.refresh(source)
    return EpgImportResultOut(source=EpgSourceOut.model_validate(source), **result.as_dict())


@router.get("/sources/{source_id}/programmes", response_model=list[EpgProgrammeOut], summary="Programmes d'une source")
def source_programmes(
    source_id: str,
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EpgProgrammeOut]:
    _owned_source(source_id, user, db)
    rows = db.scalars(
        select(EpgProgramme)
        .where(EpgProgramme.source_id == source_id, EpgProgramme.stop_at >= datetime.now(UTC))
        .order_by(EpgProgramme.start_at)
        .limit(limit)
    ).all()
    return [EpgProgrammeOut.model_validate(row) for row in rows]


@router.get("/guide", response_model=list[EpgProgrammeOut], summary="Guide TV (fenêtre horaire)")
def guide(
    channel_id: str | None = Query(None),
    hours: int = Query(12, ge=1, le=72),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EpgProgrammeOut]:
    now = datetime.now(UTC)
    window_end = now + timedelta(hours=hours)
    query = select(EpgProgramme).where(
        and_(EpgProgramme.stop_at >= now, EpgProgramme.start_at <= window_end)
    )
    if channel_id:
        query = query.where(EpgProgramme.channel_id == channel_id)
    rows = db.scalars(query.order_by(EpgProgramme.start_at).limit(2000)).all()
    return [EpgProgrammeOut.model_validate(row) for row in rows]


@router.delete("/sources/{source_id}", response_model=Message, summary="Supprimer une source EPG")
def delete_source(
    source_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    source = _owned_source(source_id, user, db)
    db.delete(source)
    db.commit()
    return Message(message="Source EPG supprimée")


@router.get("/now/{channel_id}", response_model=dict, summary="En cours / à suivre pour une chaîne")
def now_next(
    channel_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(EpgProgramme)
        .where(EpgProgramme.channel_id == channel_id, EpgProgramme.stop_at >= now)
        .order_by(EpgProgramme.start_at)
        .limit(2)
    ).all()
    return {
        "current": EpgProgrammeOut.model_validate(rows[0]).model_dump() if rows else None,
        "next": EpgProgrammeOut.model_validate(rows[1]).model_dump() if len(rows) > 1 else None,
    }
