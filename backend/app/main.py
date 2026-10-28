"""Point d'entrée FastAPI de PrimeTV.

Lancement développement :
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Production : voir backend/Dockerfile (gunicorn + uvicorn workers).
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.v1 import api_router
from app.api.v1.auth import admin_router, profiles_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.http import close_http_client
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import rate_limit_middleware
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import *  # noqa: F401,F403 - enregistre tous les modèles dans les métadonnées
from app.services.importer import ensure_reference_data
from app.services.seed import create_default_admin, seed_demo_catalog

logger = get_logger("primetv")

DESCRIPTION = """
API REST de **PrimeTV**, plateforme IPTV open source (FastAPI + PostgreSQL + Redis).

### Fonctionnalités
* import de playlists **M3U / M3U8 / M3U Plus**, fichiers, URLs et portails **Xtream Codes** ;
* flux **HLS**, **DASH**, MP4, MPEG-TS et radios ;
* EPG **XMLTV** avec association automatique des chaînes ;
* classification automatique (catégorie, langue, qualité, bouquet) ;
* favoris, historique et reprise de lecture **par profil** ;
* scan/actualisation avec détection des flux **chiffrés** (AES-128, ClearKey, DRM) ;
* proxy de lecture (CORS + réécriture HLS) et transmission de clés **fournies par l'utilisateur**.

### ⚖️ Usage responsable
PrimeTV est un lecteur : il ne fournit aucun contenu ni aucune clé. N'importez que des
playlists et des flux que vous êtes autorisé à regarder. Le contournement de DRM
(Widevine/PlayReady/FairPlay) n'est **pas** implémenté : ces flux sont signalés et exclus.

### Authentification
`POST /api/v1/auth/login` → récupérez `access_token` puis envoyez
`Authorization: Bearer <token>`. Les routes de profil acceptent l'en-tête `X-Profile-Id`.
"""

TAGS_METADATA = [
    {"name": "Système", "description": "Santé, version et configuration publique."},
    {"name": "Authentification", "description": "Comptes, JWT et rafraîchissement."},
    {"name": "Profils", "description": "Multi-profils (famille, enfant, invité)."},
    {"name": "Administration", "description": "Gestion des utilisateurs (admin)."},
    {"name": "Catalogue", "description": "Catégories, langues, bouquets, filtres."},
    {"name": "Chaînes", "description": "Recherche, détail, lecture, clés ClearKey."},
    {"name": "Fournisseurs", "description": "Fournisseurs IPTV autorisés."},
    {"name": "Playlists", "description": "Import et synchronisation M3U/Xtream."},
    {"name": "EPG", "description": "Sources XMLTV et programmes."},
    {"name": "Favoris", "description": "Favoris par profil."},
    {"name": "Historique", "description": "Historique et reprise de lecture."},
    {"name": "Scan & actualisation", "description": "Scan réseau, détection du chiffrement."},
    {"name": "Statistiques", "description": "Tableau de bord et activité."},
    {"name": "Réglages", "description": "Préférences utilisateur."},
    {"name": "Lecture & proxy", "description": "Proxy HLS/DASH et clés de lecture."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialisation : logs, schéma, données de référence, admin et démo."""
    configure_logging()
    logger.info("Démarrage de %s %s (env=%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENV)
    if settings.AUTO_CREATE_SCHEMA:
        Base.metadata.create_all(bind=engine)
        logger.info("Schéma de base de données vérifié")
    with SessionLocal() as db:
        ensure_reference_data(db)
        db.commit()
        admin = create_default_admin(db)
        if settings.SEED_DEMO_DATA:
            from sqlalchemy import select

            from app.models.user import User

            target = admin or db.scalars(select(User).where(User.role == "admin")).first()
            if target:
                seed_demo_catalog(db, target)
    if settings.SECRET_KEY.startswith("dev-only"):
        logger.warning("SECRET_KEY de développement détectée : à remplacer avant toute mise en production")
    yield
    close_http_client()
    logger.info("Arrêt de PrimeTV")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=settings.APP_VERSION,
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
    lifespan=lifespan,
    contact={"name": "PrimeTV", "url": "https://github.com/HamdiSouissi/primeTV"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# ---------------------------------------------------------------- Middlewares
app.add_middleware(GZipMiddleware, minimum_size=1000)
if settings.trusted_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
if settings.cors_origins != ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-Process-Time", "X-RateLimit-Remaining"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-Process-Time", "X-RateLimit-Remaining"],
    )
if settings.FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Identifiant de requête, mesure de latence, en-têtes de sécurité."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started = time.perf_counter()
    response = await rate_limit_middleware(request, call_next)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Process-Time"] = str(duration_ms)
    if settings.SECURE_HEADERS:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
    if request.url.path.startswith(settings.API_V1_PREFIX) and request.url.path != "/api/v1/healthz":
        logger.debug("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


register_exception_handlers(app)

# ---------------------------------------------------------------- Routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(profiles_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def index():
    if settings.DOCS_ENABLED:
        return RedirectResponse("/docs")
    return JSONResponse(
        {"name": settings.APP_NAME, "version": settings.APP_VERSION, "api": settings.API_V1_PREFIX}
    )


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Sonde utilisée par Docker/Compose/Kubernetes."""
    from sqlalchemy import text

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "version": settings.APP_VERSION}
    except Exception as exc:  # pragma: no cover
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(exc)})


def custom_openapi():
    """OpenAPI enrichi (serveurs, sécurité Bearer) pour Swagger UI."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=TAGS_METADATA,
        contact=app.contact,
        license_info=app.license_info,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    schema["servers"] = [
        {"url": settings.PUBLIC_BASE_URL, "description": "Serveur courant"},
        {"url": "http://localhost:8000", "description": "Développement local"},
    ]
    for path, methods in schema.get("paths", {}).items():
        if "/auth/login" in path or "/auth/register" in path or path.endswith("/healthz"):
            continue
        for method in methods.values():
            method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]
