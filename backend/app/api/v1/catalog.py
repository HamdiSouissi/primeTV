"""Catalogue : catégories, langues, bouquets et filtres disponibles."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_active_profile, get_current_user
from app.db.session import get_db
from app.models.activity import Favorite
from app.models.catalog import Bouquet, Category, Channel, Language, channel_bouquets
from app.models.user import Profile, User
from app.schemas.catalog import BouquetOut, CategoryOut, LanguageOut
from app.schemas.common import FacetCount

router = APIRouter()


@router.get("/categories", response_model=list[CategoryOut], summary="Catégories")
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    rows = db.scalars(select(Category).order_by(Category.position, Category.name)).all()
    return [CategoryOut.model_validate(row) for row in rows]


@router.get("/languages", response_model=list[LanguageOut], summary="Langues")
def list_languages(db: Session = Depends(get_db)) -> list[LanguageOut]:
    rows = db.scalars(select(Language).order_by(Language.position, Language.name)).all()
    return [LanguageOut.model_validate(row) for row in rows]


@router.get("/bouquets", response_model=list[BouquetOut], summary="Bouquets")
def list_bouquets(db: Session = Depends(get_db)) -> list[BouquetOut]:
    rows = db.scalars(select(Bouquet).order_by(Bouquet.name)).all()
    return [BouquetOut.model_validate(row) for row in rows]


@router.get("/facets", response_model=dict, summary="Compteurs par catégorie, langue et bouquet")
def facets(
    user: User = Depends(get_current_user),
    profile: Profile = Depends(get_active_profile),
    db: Session = Depends(get_db),
) -> dict:
    """Alimente les filtres de l'interface (avec le nombre de chaînes par valeur)."""
    category_rows = db.execute(
        select(Category.slug, Category.name, Category.color, Category.icon, func.count(Channel.id))
        .join(Channel, Channel.category_id == Category.id)
        .group_by(Category.slug, Category.name, Category.color, Category.icon, Category.position)
        .order_by(Category.position)
    ).all()
    language_rows = db.execute(
        select(Language.code, Language.name, Language.flag, func.count(Channel.id))
        .join(Channel, Channel.language_id == Language.id)
        .group_by(Language.code, Language.name, Language.flag, Language.position)
        .order_by(Language.position)
    ).all()
    bouquet_rows = db.execute(
        select(Bouquet.id, Bouquet.name, func.count(channel_bouquets.c.channel_id))
        .join(channel_bouquets, channel_bouquets.c.bouquet_id == Bouquet.id)
        .group_by(Bouquet.id, Bouquet.name)
        .order_by(func.count(channel_bouquets.c.channel_id).desc())
    ).all()
    favorite_count = db.scalar(
        select(func.count(Favorite.id)).where(Favorite.profile_id == profile.id)
    )
    totals = {
        "channels": db.scalar(select(func.count(Channel.id))) or 0,
        "radios": db.scalar(select(func.count(Channel.id)).where(Channel.is_radio.is_(True))) or 0,
        "encrypted": db.scalar(select(func.count(Channel.id)).where(Channel.is_encrypted.is_(True))) or 0,
        "active": db.scalar(select(func.count(Channel.id)).where(Channel.status == "active")) or 0,
        "favorites": favorite_count or 0,
    }
    return {
        "categories": [
            {"slug": slug, "name": name, "color": color, "icon": icon, "count": count}
            for slug, name, color, icon, count in category_rows
        ],
        "languages": [
            {"code": code, "name": name, "flag": flag, "count": count}
            for code, name, flag, count in language_rows
        ],
        "bouquets": [{"id": item_id, "name": name, "count": count} for item_id, name, count in bouquet_rows],
        "totals": totals,
        "user_id": user.id,
    }


@router.get("/quick-filters", response_model=list[FacetCount], summary="Filtres rapides (sport & arabe en tête)")
def quick_filters(db: Session = Depends(get_db)) -> list[FacetCount]:
    """Raccourcis proposés en haut de l'interface."""
    shortcuts = [
        ("sport", "Sport"),
        ("ar", "Arabic"),
        ("news", "News"),
        ("fr", "French"),
        ("movies", "Movies"),
        ("kids", "Kids"),
        ("music", "Music"),
        ("religion", "Religion"),
        ("documentary", "Documentary"),
    ]
    results: list[FacetCount] = []
    for slug, label in shortcuts:
        category = db.scalars(select(Category).where(Category.slug == slug)).first()
        if category:
            count = db.scalar(select(func.count(Channel.id)).where(Channel.category_id == category.id)) or 0
            if count:
                results.append(
                    FacetCount(id=category.id, slug=slug, name=label, count=count, color=category.color, icon=category.icon)
                )
            continue
        language = db.scalars(select(Language).where(Language.code == slug)).first()
        if language:
            count = db.scalar(select(func.count(Channel.id)).where(Channel.language_id == language.id)) or 0
            if count:
                results.append(FacetCount(id=language.id, slug=slug, name=label, count=count, flag=language.flag))
    return results
