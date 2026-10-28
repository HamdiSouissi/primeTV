"""Routeur v1 : agrège tous les sous-routeurs."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    catalog,
    channels,
    epg,
    favorites,
    history,
    playlists,
    providers,
    scan,
    stats,
    streams,
    system,
)
from app.api.v1 import (
    settings as settings_router,
)

api_router = APIRouter()
api_router.include_router(system.router, tags=["Système"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentification"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["Catalogue"])
api_router.include_router(channels.router, prefix="/channels", tags=["Chaînes"])
api_router.include_router(providers.router, prefix="/providers", tags=["Fournisseurs"])
api_router.include_router(playlists.router, prefix="/playlists", tags=["Playlists"])
api_router.include_router(epg.router, prefix="/epg", tags=["EPG"])
api_router.include_router(favorites.router, prefix="/favorites", tags=["Favoris"])
api_router.include_router(history.router, prefix="/history", tags=["Historique"])
api_router.include_router(scan.router, prefix="/scan", tags=["Scan & actualisation"])
api_router.include_router(stats.router, prefix="/stats", tags=["Statistiques"])
api_router.include_router(settings_router.router, prefix="/settings", tags=["Réglages"])
api_router.include_router(streams.router, prefix="/streams", tags=["Lecture & proxy"])
