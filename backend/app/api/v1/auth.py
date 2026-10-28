"""Authentification JWT, comptes et profils."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.config import settings
from app.core.passwords import hash_password, needs_rehash, verify_password
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models.user import Profile, User
from app.schemas.auth import (
    LoginIn,
    PasswordChangeIn,
    ProfileIn,
    ProfileOut,
    ProfileUpdate,
    RefreshIn,
    RegisterIn,
    TokenOut,
    UserAdminUpdate,
    UserOut,
    UserUpdate,
)
from app.schemas.common import Message

router = APIRouter()


def _issue_tokens(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED, summary="Créer un compte")
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Les inscriptions sont désactivées")
    exists = db.scalars(
        select(User).where(or_(User.email == payload.email.lower(), User.username == payload.username))
    ).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email ou nom d'utilisateur déjà utilisé")
    user = User(
        email=payload.email.lower(),
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="user",
    )
    db.add(user)
    db.flush()
    db.add(
        Profile(
            user_id=user.id,
            name=payload.profile_name or "Principal",
            is_default=True,
            avatar="user",
        )
    )
    db.commit()
    db.refresh(user)
    return _issue_tokens(user)


@router.post("/login", response_model=TokenOut, summary="Se connecter (email ou pseudo)")
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    identifier = payload.email.lower().strip()
    user = db.scalars(select(User).where(or_(User.email == identifier, User.username == payload.email.strip()))).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    user.last_login_at = datetime.now(UTC).isoformat()
    db.commit()
    db.refresh(user)
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenOut, summary="Rafraîchir les jetons")
def refresh(payload: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    user = db.get(User, claims.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Jeton invalide")
    return _issue_tokens(user)


@router.get("/me", response_model=UserOut, summary="Profil du compte connecté")
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut, summary="Mettre à jour son compte")
def update_me(payload: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    for attribute, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, attribute, value.lower() if attribute == "email" and value else value)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/change-password", response_model=Message, summary="Changer son mot de passe")
def change_password(
    payload: PasswordChangeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return Message(message="Mot de passe mis à jour")


# ---------------------------------------------------------------- Profils
profiles_router = APIRouter(prefix="/profiles", tags=["Profils"])


@profiles_router.get("", response_model=list[ProfileOut], summary="Lister les profils")
def list_profiles(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ProfileOut]:
    profiles = db.scalars(
        select(Profile).where(Profile.user_id == user.id).order_by(Profile.is_default.desc(), Profile.created_at)
    ).all()
    return [
        ProfileOut.model_validate(profile).model_copy(update={"has_pin": bool(profile.pin_hash)})
        for profile in profiles
    ]


@profiles_router.post("", response_model=ProfileOut, status_code=201, summary="Créer un profil")
def create_profile(
    payload: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileOut:
    data = payload.model_dump(exclude={"pin"})
    profile = Profile(
        user_id=user.id,
        pin_hash=hash_password(payload.pin, min_length=4) if payload.pin else None,
        **data,
    )
    if payload.is_default:
        db.query(Profile).filter(Profile.user_id == user.id).update({"is_default": False})
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return ProfileOut.model_validate(profile).model_copy(update={"has_pin": bool(profile.pin_hash)})


@profiles_router.patch("/{profile_id}", response_model=ProfileOut, summary="Modifier un profil")
def update_profile(
    profile_id: str,
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    profile = db.get(Profile, profile_id)
    if not profile or profile.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    data = payload.model_dump(exclude_unset=True)
    pin = data.pop("pin", None)
    if pin:
        profile.pin_hash = hash_password(pin, min_length=4)
    if data.get("is_default"):
        db.query(Profile).filter(Profile.user_id == user.id, Profile.id != profile.id).update({"is_default": False})
    for attribute, value in data.items():
        setattr(profile, attribute, value)
    db.commit()
    db.refresh(profile)
    return ProfileOut.model_validate(profile).model_copy(update={"has_pin": bool(profile.pin_hash)})


@profiles_router.delete("/{profile_id}", response_model=Message, summary="Supprimer un profil")
def delete_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Message:
    profiles = db.scalars(select(Profile).where(Profile.user_id == user.id)).all()
    profile = next((item for item in profiles if item.id == profile_id), None)
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil introuvable")
    if len(profiles) <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Au moins un profil est requis")
    db.delete(profile)
    db.commit()
    return Message(message="Profil supprimé")


# ---------------------------------------------------------------- Administration
admin_router = APIRouter(prefix="/admin", tags=["Administration"])


@admin_router.get("/users", response_model=list[UserOut], summary="Lister les utilisateurs (admin)")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[UserOut]:
    return [UserOut.model_validate(user) for user in db.scalars(select(User).order_by(User.created_at))]


@admin_router.patch("/users/{user_id}", response_model=UserOut, summary="Modifier un utilisateur (admin)")
def admin_update_user(
    user_id: str,
    payload: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")
    if target.id == admin.id and payload.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Impossible de désactiver son propre compte")
    for attribute, value in payload.model_dump(exclude_unset=True).items():
        setattr(target, attribute, value)
    db.commit()
    db.refresh(target)
    return UserOut.model_validate(target)
