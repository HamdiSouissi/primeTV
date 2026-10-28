# Configuration

Toute la configuration passe par des variables d'environnement (fichier `.env` à la racine).
Les valeurs par défaut sont dans `backend/app/core/config.py` (classe `Settings`).

> ⚠️ Après modification de `.env` : `docker compose up -d` (recrée les conteneurs concernés).
> Le cache des réglages est chargé au démarrage du backend.

---

## Application

| Variable | Défaut | Description |
|---|---|---|
| `APP_NAME` | `PrimeTV` | Nom affiché dans OpenAPI et les logs |
| `APP_VERSION` | `1.0.0` | Version exposée par `/healthz` |
| `ENV` | `development` | `development` \| `staging` \| `production` (active HSTS) |
| `DEBUG` | `True` | Mode debug (logs détaillés) |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | URL publique utilisée dans OpenAPI |
| `API_V1_PREFIX` | `/api/v1` | Préfixe de l'API |
| `DOCS_ENABLED` | `True` | Expose `/docs`, `/redoc`, `/openapi.json` |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `LOG_JSON` | `False` | Logs JSON (production / agrégation) |

## Sécurité

| Variable | Défaut | Description |
|---|---|---|
| `SECRET_KEY` | dev-only | **Obligatoire** ≥ 16 caractères. Signe les JWT et chiffre les identifiants fournisseurs. `openssl rand -base64 48` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Durée du jeton d'accès (12 h) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | Durée du jeton de rafraîchissement |
| `ALLOW_REGISTRATION` | `True` | Autoriser `POST /auth/register` |
| `CORS_ORIGINS` | `*` | Liste séparée par virgules, ou `*` |
| `TRUSTED_HOSTS` | `*` | Hôtes autorisés (`Host` header) |
| `SECURE_HEADERS` | `True` | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS en prod |
| `RATE_LIMIT_ENABLED` | `True` | Active la limitation de débit |
| `RATE_LIMIT_REQUESTS` | `300` | Requêtes autorisées par fenêtre et par client |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Taille de la fenêtre |
| `FORCE_HTTPS` | `False` | Redirection 307 vers HTTPS (utile derrière proxy) |

> Changer `SECRET_KEY` invalide les jetons **et** les mots de passe fournisseurs chiffrés
> (`cryptography.Fernet`, clé dérivée du secret). Réenregistrez-les après rotation.

## Base de données

| Variable | Défaut | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./primetv_local.db` | `postgresql+psycopg://user:pass@postgres:5432/primetv` |
| `DB_ECHO` | `False` | Journalise le SQL |
| `DB_POOL_SIZE` | `10` | Connexions en pool |
| `DB_MAX_OVERFLOW` | `20` | Débordement autorisé |
| `AUTO_CREATE_SCHEMA` | `True` | Crée les tables au démarrage (idempotent) |

## Cache & Redis

| Variable | Défaut | Description |
|---|---|---|
| `REDIS_URL` | vide | Vide → cache mémoire interne (dev/tests) |
| `CACHE_TTL_SECONDS` | `60` | TTL par défaut |
| `CACHE_ENABLED` | `True` | Interrupteur global |

Le cache stocke les réponses JSON (facettes, statistiques) et les compteurs de débit.
Si Redis tombe, PrimeTV bascule automatiquement en mémoire (aucune indisponibilité).

## Import & scan

| Variable | Défaut | Description |
|---|---|---|
| `HTTP_TIMEOUT_SECONDS` | `25` | Timeout des téléchargements (playlists, XMLTV) |
| `HTTP_USER_AGENT` | `PrimeTV/1.0` | User-Agent envoyé aux sources |
| `MAX_PLAYLIST_BYTES` | `41943040` (40 Mo) | Taille maximale d'une playlist |
| `MAX_IMPORT_CHANNELS` | `60000` | Chaînes max importées par playlist |
| `PROBE_CONCURRENCY` | `8` | Tests réseau simultanés pendant un scan |
| `PROBE_TIMEOUT_SECONDS` | `8` | Timeout par flux testé |
| `SCAN_MAX_CHANNELS` | `5000` | Chaînes max par job de scan |
| `ALLOW_PRIVATE_STREAM_HOSTS` | `False` | Autorise les URL privées/LAN (danger SSRF, à réserver au LAN) |

## Priorisation de l'interface

| Variable | Défaut | Effet |
|---|---|---|
| `PRIORITY_SPORT` | `40` | Bonus de score pour la catégorie Sport |
| `PRIORITY_ARABIC` | `35` | Bonus pour la langue arabe |
| `PRIORITY_NEWS` | `20` | Bonus pour News |
| `PRIORITY_FRENCH` | `10` | Bonus pour le français |

Le tri par défaut de `/channels` est `priority DESC, name ASC`. Augmentez `PRIORITY_ARABIC`
pour faire remonter davantage les chaînes arabes.

## Compte initial & démonstration

| Variable | Défaut | Description |
|---|---|---|
| `DEFAULT_ADMIN_EMAIL` | `admin@primetv.io` | Compte admin créé si la base est vide |
| `DEFAULT_ADMIN_PASSWORD` | `PrimeTV#2026` | **À changer immédiatement** |
| `SEED_DEMO_DATA` | `False` | Crée un fournisseur + playlist de démonstration (10 flux publics) |

## Frontend (build)

| Variable | Défaut | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Base d'appel API côté navigateur (même origine conseillée) |
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Cible du proxy **Vite** en développement |

Le proxy de lecture renvoie des URLs **relatives** (`/api/v1/streams/proxy?...`) : le web, Nginx et
l'application web fonctionne donc en même origine (aucune URL d'API à configurer côté client).

## Traefik

| Variable | Défaut | Description |
|---|---|---|
| `TRAEFIK_DOMAIN` | `primetv.localhost` | Domaine servi |
| `TRAEFIK_ACME_EMAIL` | `admin@example.com` | E-mail Let's Encrypt |
| `TRAEFIK_BASIC_AUTH_USERS` | vide | `user:hash` (htpasswd) pour protéger l'accès |

## Docker

| Variable | Défaut | Description |
|---|---|---|
| `HTTP_PORT` | `8080` | Port HTTP exposé par Nginx |
| `HTTPS_PORT` | `8443` | Port HTTPS exposé par Nginx |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `primetv` / `primetv` / — | Base de données |
| `WEB_CONCURRENCY` | `4` | Workers Gunicorn/Uvicorn |

---

## Exemple `.env` de production

```env
ENV=production
DEBUG=false
PUBLIC_BASE_URL=https://tv.example.com
SECRET_KEY=<openssl rand -base64 48>
POSTGRES_PASSWORD=<mot de passe fort>
DATABASE_URL=postgresql+psycopg://primetv:<mot de passe fort>@postgres:5432/primetv
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=https://tv.example.com
TRUSTED_HOSTS=tv.example.com,localhost
FORCE_HTTPS=true
SECURE_HEADERS=true
RATE_LIMIT_REQUESTS=180
ALLOW_REGISTRATION=false
SEED_DEMO_DATA=false
DEFAULT_ADMIN_PASSWORD=<mot de passe unique>
LOG_JSON=true
```

## Réglages utilisateur

En plus des variables d'environnement, chaque utilisateur peut enregistrer des préférences via
`PUT /api/v1/settings` (clé/valeur JSON), par exemple :

```json
{ "key": "player", "value": { "autoplay": true, "defaultQuality": "auto", "subtitles": "fr" } }
```
