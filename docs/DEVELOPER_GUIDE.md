# Guide développeur

## 1. Mise en route

```bash
git clone https://github.com/HamdiSouissi/primeTV.git
cd primeTV
./scripts/dev.sh
```

| Service | URL | Rechargement |
|---|---|---|
| API FastAPI | http://localhost:8000/docs | `--reload` |
| Web Vite | http://localhost:5173 | HMR |
| Base | SQLite `backend/primetv_local.db` | recréée au besoin |

Tests : `./scripts/test-all.sh` (lint + pytest + typecheck + Vitest + build + smoke API).

## 2. Structure du backend

```
backend/app/
├── main.py            # app FastAPI, middlewares, OpenAPI, lifespan (schéma + seed)
├── core/
│   ├── config.py      # Settings (pydantic-settings, .env)
│   ├── security.py    # JWT sign/verify
│   ├── passwords.py   # PBKDF2-SHA256
│   ├── crypto.py      # Fernet (identifiants fournisseurs)
│   ├── cache.py       # Redis ou mémoire (TTL, incréments)
│   ├── rate_limit.py  # middleware fenêtre fixe
│   ├── errors.py      # format d'erreur {error:{code,message,details}}
│   ├── pagination.py  # PageParams + enveloppe Page
│   ├── http.py        # httpx partagé + validation anti-SSRF
│   └── logging.py     # texte ou JSON
├── db/
│   ├── base.py        # Base, UUIDMixin, TimestampMixin, UTCDateTime
│   └── session.py     # engine + SessionLocal + get_db
├── models/            # SQLAlchemy 2 (Mapped[...])
├── schemas/           # Pydantic v2
├── api/v1/            # un module par domaine + deps.py (auth, profil actif)
├── services/          # logique métier pure, testable sans HTTP
└── utils/
```

**Règle de dépendance** : `api → services → models/db` ; `services` ne dépend jamais de FastAPI
(sauf `HTTPException` pour les erreurs de flux, assumé).

## 3. Cycle de vie d'une requête

1. Nginx → Gunicorn (Uvicorn worker) → FastAPI.
2. Middlewares : GZip, CORS/TrustedHost, `observability_middleware` (request-id, latence, en-têtes,
   rate limit) puis gestionnaire d'erreurs.
3. Dépendances : `get_db` (session par requête), `get_current_user` (JWT), `get_active_profile`
   (`X-Profile-Id`), `page_params`.
4. Route → service → ORM → Pydantic (`response_model`).
5. Commit explicite dans le service/route ; rollback automatique en cas d'exception SQLAlchemy.

## 4. Ajouter une fonctionnalité

### 4.1 Nouvelle catégorie de chaînes

`backend/app/services/classifier.py` → `CATEGORY_RULES` :

```python
"esport": {
    "name": "eSport", "icon": "gamepad-2", "color": "#6366f1",
    "keywords": ["esport", "gaming", "twitch", "league of legends", "رياضات إلكترونية"],
},
```

Redémarrez : la catégorie est créée au prochain import (`ensure_reference_data`) et apparaît dans
`/catalog/categories`, `/config` et l'UI.

### 4.2 Nouvelle langue

`LANGUAGE_RULES` + éventuellement `COUNTRY_LANGUAGE` pour le pays associé.

### 4.3 Nouveau type de source (ex. fournisseur « Stalker »)

1. `services/stalker.py` : classe/fonction retournant une `ParsedPlaylist` (liste de `ParsedChannel`).
2. `api/v1/playlists.py` : route `POST /playlists/stalker` qui appelle le service puis
   `import_playlist_content(...)`.
3. Schéma Pydantic + tests.

Les `ParsedChannel` n'ont besoin que de `name`, `url` et des métadonnées optionnelles : le reste
(classification, chiffrement, bouquets) est automatique.

### 4.4 Nouvel endpoint

```python
# app/api/v1/example.py
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/ping", summary="Exemple")
def ping(user: User = Depends(get_current_user)) -> dict:
    return {"pong": True, "user": user.id}
```

Puis dans `app/api/v1/__init__.py` :

```python
from app.api.v1 import example
api_router.include_router(example.router, prefix="/example", tags=["Exemple"])
```

Ajoutez un `tags` dans `TAGS_METADATA` (main.py) et la route apparaît dans Swagger.

### 4.5 Frontend : nouvelle page

1. `web/src/pages/MaPage.tsx` (composants dans `components/`, requêtes dans `hooks/queries.ts`).
2. Route dans `web/src/App.tsx` (sous `ProtectedLayout`).
3. Entrée de navigation dans `web/src/components/Layout.tsx`.

### 4.6 Mobile : nouvel écran

1. `mobile/lib/screens/mon_ecran.dart` (`StatefulWidget`, `context.watch<AppState>()`).
2. Ajoutez un `NavigationDestination` dans `home_shell.dart` ou poussez la route via `Navigator`.

## 5. Base de données

### Modèles

| Table | Champs clés |
|---|---|
| `users` | email, username, password_hash, role, is_active |
| `profiles` | user_id, name, is_kids, is_default, pin_hash, preferences |
| `providers` | user_id, name, kind, base_url, username, password (chiffré), epg_url |
| `playlists` | user_id, provider_id, source_type, url, channel_count, extras (contenu, warnings) |
| `categories` | name, slug, icon, color, position |
| `languages` | code, name, native_name, flag, position |
| `bouquets` | name, slug, provider_id |
| `channels` | playlist_id, category_id, language_id, name, normalized_name, stream_url, stream_key, stream_type, is_radio, is_encrypted, encryption, drm_systems, clear_keys, status, priority, extras |
| `channel_bouquets` | association N-N |
| `epg_sources` | user_id, name, url, programme_count, status |
| `epg_programmes` | source_id, channel_id, xmltv_id, title, start_at, stop_at |
| `favorites` | profile_id, channel_id (unique ensemble) |
| `history` | profile_id, channel_id, position_seconds, watched_at |
| `scan_jobs` | status, progress, total, active, offline, encrypted, drm_protected, logs |
| `settings` | user_id (nullable), key, value |
| `activity_logs` | user_id, action, message, level, context |

* Identifiants : UUID stockés en `CHAR(36)` (portable SQLite/PostgreSQL).
* `stream_key = sha256(url)[:40]` : unicité `(playlist_id, stream_key)` → imports idempotents.
* Datetimes : type `UTCDateTime` (toujours UTC, y compris sous SQLite).

### Migrations

Le schéma est créé au démarrage (`AUTO_CREATE_SCHEMA=true`) ; suffisant pour une installation neuve.
Pour faire évoluer un schéma existant, ajoutez Alembic :

```bash
cd backend
.venv/bin/pip install alembic
.venv/bin/alembic init migrations
# éditez migrations/env.py : target_metadata = Base.metadata ; import app.models
.venv/bin/alembic revision --autogenerate -m "ajout table x"
.venv/bin/alembic upgrade head
```

Toute modification de modèle doit être accompagnée : (1) d'une migration, (2) d'une note dans le
CHANGELOG, (3) d'un test si le comportement change.

## 6. Tests

```bash
cd backend
.venv/bin/python -m pytest -q                  # tous
.venv/bin/python -m pytest tests/test_parsing.py -q -k m3u
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

* `tests/conftest.py` force SQLite temporaire, `SEED_DEMO_DATA=true`, rate limit désactivé,
  et fournit `client`, `admin_headers`, `user_headers`, `demo_channel`.
* Les tests réseau ne doivent **jamais** dépendre d'Internet : le scan est testé avec `probe=false`.

Frontend :

```bash
cd web && npm run test -- --watch      # mode interactif
```

Mobile :

```bash
cd mobile && flutter test
```

## 7. Conventions

* Python : `ruff check app tests` (ligne 110), annotations, docstrings en français, pas de `print`.
* TypeScript : `strict`, pas de `any` implicite, composants fonctionnels, hooks, TanStack Query.
* Dart : `flutter analyze`, `flutter_lints`, widgets const quand possible.
* Commits : `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` (Conventional Commits).
* Une fonctionnalité = code + test + documentation.

## 8. Sécurité côté code

* Toute URL distante passe par `validate_remote_url()` (schémas http/https, blocage IP privées).
* Le proxy vérifie que l'hôte demandé appartient au domaine du flux (`assert_host_allowed`).
* Les mots de passe ne sortent jamais : `ProviderOut.has_password` seulement.
* Clés ClearKey : stockées par chaîne (`channels.clear_keys`), jamais journalisées.
* Ne jamais concaténer du SQL : utilisez l'ORM ou `text()` avec paramètres liés.

## 9. Ajouts à venir (pistes)

* WebSocket/SSE pour la progression de scan (au lieu du polling).
* Chiffrement des clés ClearKey au repos (clé par chaîne, Fernet).
* Enregistrement programmé (PVR) — attention au stockage et aux droits.
* Multi-tenancy strict du catalogue (chaînes par utilisateur).
* Prometheus `/metrics` + dashboard Grafana.
