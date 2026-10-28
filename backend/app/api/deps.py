"""Dépendances partagées des routeurs (authentification, profil actif, filtres)."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.provider import Playlist, Provider
from app.models.user import Profile, User

bearer_scheme = HTTPBearer(auto_error=False)


def _load_user_from_token(db: Session, token: str) -> User:
    payload = decode_token(token, expected_type="access")
    user = db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur inexistant")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé")
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Utilisateur authentifié (en-tête ``Authorization: Bearer <jwt>``)."""
    if credentials is None or not credentials.credentials:
        token = request.query_params.get("access_token")
        if not token:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Authentification requise",
                {"WWW-Authenticate": "Bearer"},
            )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = _load_user_from_token(db, credentials.credentials)
    request.state.user_id = user.id
    return user


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Comme ``get_current_user`` mais retourne None si le jeton est absent."""
    token = credentials.credentials if credentials else request.query_params.get("access_token")
    if not token:
        return None
    try:
        return _load_user_from_token(db, token)
    except HTTPException:
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits administrateur requis")
    return user


def get_active_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    profile_id: str | None = Header(default=None, alias="X-Profile-Id"),
    profile: str | None = Query(default=None, include_in_schema=False),
) -> Profile:
    """Profil actif : en-tête ``X-Profile-Id``, sinon le profil par défaut."""
    wanted = profile_id or profile
    if wanted:
        found = db.get(Profile, wanted)
        if not found or found.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
        return found
    default = db.scalars(
        select(Profile).where(Profile.user_id == user.id).order_by(Profile.is_default.desc(), Profile.created_at)
    ).first()
    if not default:
        default = Profile(user_id=user.id, name="Principal", is_default=True)
        db.add(default)
        db.commit()
        db.refresh(default)
    return default


def get_owned_provider(provider_id: str, user: User, db: Session) -> Provider:
    provider = db.get(Provider, provider_id)
    if not provider or provider.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fournisseur introuvable")
    return provider


def get_owned_playlist(playlist_id: str, user: User, db: Session) -> Playlist:
    playlist = db.get(Playlist, playlist_id)
    if not playlist or playlist.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Playlist introuvable")
    return playlist
