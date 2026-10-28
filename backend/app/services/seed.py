"""Données de démonstration (facultatif) : chaînes libres et exemple de catalogue.

Toutes les entrées pointent vers des sources publiques de démonstration
(Apple, Mux, Bitmovin, radio SomaFM). Aucun contenu piraté n'est inclus.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.passwords import hash_password
from app.models.catalog import Channel
from app.models.provider import Playlist, Provider
from app.models.user import Profile, User
from app.services.importer import ensure_reference_data, import_playlist_content
from app.services.m3u import parse_m3u

logger = get_logger(__name__)

DEMO_M3U = """#EXTM3U url-tvg="https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml"
#EXTINF:-1 tvg-id="demo.sport.1" tvg-name="beIN Sports Demo" tvg-logo="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/BeIN_Sports_Logo.svg/240px-BeIN_Sports_Logo.svg.png" group-title="Sport | Arabic",beIN SPORTS Demo HD
https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
#EXTINF:-1 tvg-id="demo.news.1" tvg-name="Al Jazeera Demo" group-title="News | Arabic",الجزيرة مباشر Demo
https://live-hls-web-aja.getaj.net/AJA/index.m3u8
#EXTINF:-1 tvg-id="demo.news.2" tvg-name="France 24 FR" group-title="News | French",France 24 Français
https://static.france24.com/live/F24_FR_HI_HLS/live_web.m3u8
#EXTINF:-1 tvg-id="demo.news.3" tvg-name="DW English" group-title="News | English",DW English HD
https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/index.m3u8
#EXTINF:-1 tvg-id="demo.movies.1" tvg-name="Mux Movies" group-title="Movies | English",Mux Movie Demo
https://test-streams.mux.dev/pts_shift/master.m3u8
#EXTINF:-1 tvg-id="demo.kids.1" tvg-name="Kids Demo" group-title="Kids | English",Kids Cartoon Demo
https://test-streams.mux.dev/tos_ismc/main.m3u8
#EXTINF:-1 tvg-id="demo.music.1" tvg-name="SomaFM Groove Salad" group-title="Music | Radio",SomaFM Groove Salad
https://ice2.somafm.com/groovesalad-128-mp3
#EXTINF:-1 tvg-id="demo.music.2" tvg-name="SomaFM Deep Space One" group-title="Music | Radio",SomaFM Deep Space One
https://ice2.somafm.com/deepspaceone-128-mp3
#EXTINF:-1 tvg-id="demo.dash.1" tvg-name="DASH Demo" group-title="Documentary | English",DASH Documentary Demo
https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps.mpd
#EXTINF:-1 tvg-id="demo.sport.2" tvg-name="Sport DASH" group-title="Sport | English",Sport DASH Demo
https://dash.akamaized.net/dash264/TestCases/1a/sony/SNE_DASH_SD_CASE1A_REVISED.mpd
"""


def create_default_admin(db: Session) -> User | None:
    """Crée le compte administrateur par défaut si la base est vide."""
    if db.scalar(select(func.count(User.id))):
        return None
    admin = User(
        email=settings.DEFAULT_ADMIN_EMAIL,
        username="admin",
        full_name="Administrateur PrimeTV",
        password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        role="admin",
    )
    db.add(admin)
    db.flush()
    db.add(Profile(user_id=admin.id, name="Principal", is_default=True, avatar="user"))
    db.commit()
    logger.warning(
        "Compte administrateur créé : %s / %s (à changer immédiatement !)",
        settings.DEFAULT_ADMIN_EMAIL,
        settings.DEFAULT_ADMIN_PASSWORD,
    )
    return admin


def seed_demo_catalog(db: Session, admin: User) -> None:
    """Crée un fournisseur + playlist de démonstration avec des flux libres."""
    if db.scalar(select(func.count(Channel.id))):
        return
    ensure_reference_data(db)
    provider = Provider(
        user_id=admin.id,
        name="Démo Free TV",
        kind="m3u",
        notes="Catalogue de démonstration (flux publics de test)",
    )
    db.add(provider)
    db.flush()
    playlist = Playlist(
        user_id=admin.id,
        provider_id=provider.id,
        name="Playlist de démonstration",
        source_type="text",
        is_active=True,
    )
    db.add(playlist)
    db.flush()
    import_playlist_content(
        db,
        playlist=playlist,
        parsed=parse_m3u(DEMO_M3U),
        provider_name=provider.name,
    )
    logger.info("Catalogue de démonstration initialisé")
