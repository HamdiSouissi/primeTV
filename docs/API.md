# Documentation API — PrimeTV v1

* **Swagger UI** : `http://localhost:8080/docs`
* **ReDoc** : `http://localhost:8080/redoc`
* **OpenAPI JSON** : `http://localhost:8080/openapi.json`
* **Base** : `http://localhost:8080/api/v1`

Toutes les routes (sauf `/config`, `/healthz`, `/auth/login`, `/auth/register`, `/auth/refresh`)
exigent un en-tête `Authorization: Bearer <access_token>`.

---

## 1. Authentification JWT

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@primetv.io","password":"PrimeTV#2026"}'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "id": "d2f4...","email":"admin@primetv.io","username":"admin",
    "full_name":"Administrateur PrimeTV","role":"admin","is_active":true
  }
}
```

* `expires_in` en secondes (`ACCESS_TOKEN_EXPIRE_MINUTES × 60`).
* Rafraîchissement : `POST /auth/refresh` avec `{"refresh_token": "..."}` → nouveaux jetons.
* Le web rafraîchit automatiquement à la première réponse 401 (une seule tentative).
* Les routes de profil acceptent `X-Profile-Id: <uuid>` (profil par défaut sinon).

---

## 2. Conventions

### Pagination
`?page=1&page_size=24&sort=priority&order=desc` → 

```json
{ "items": [], "total": 120, "page": 1, "page_size": 24, "pages": 5 }
```

`page_size` : 1–200. `sort` ∈ `priority, name, created_at, updated_at, quality, status, last_checked_at`.

### Erreurs
Format stable, quel que soit l'endpoint :

```json
{ "error": { "code": "not_found", "message": "Chaîne introuvable", "details": null } }
```

| HTTP | `code` | Cas |
|---|---|---|
| 400 | `http_error` | Requête invalide / URL refusée |
| 401 | `unauthorized` | Jeton absent, expiré ou invalide |
| 403 | `forbidden` | Droits insuffisants, compte désactivé, proxy refusé |
| 404 | `not_found` | Ressource inexistante |
| 409 | `conflict` | Doublon (email, nom de fournisseur…) |
| 422 | `validation_error` | Schéma Pydantic (`details` = liste des champs) |
| 429 | `rate_limited` | Limite de débit (`Retry-After`) |
| 500 | `internal_error` / `database_error` | Erreur serveur (logs corrélés `X-Request-Id`) |

### En-têtes utiles
`X-Request-Id`, `X-Process-Time`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`.

---

## 3. Routes

### 3.1 Système (public)

| Méthode | Route | Description |
|---|---|---|
| GET | `/healthz` | Sonde (base incluse) |
| GET | `/readyz` | Disponibilité |
| GET | `/config` | Configuration publique : catégories, langues, niveaux de qualité |

### 3.2 Authentification & comptes

| Méthode | Route | Corps / Notes |
|---|---|---|
| POST | `/auth/register` | `{email, username, password, full_name?}` → jetons |
| POST | `/auth/login` | `{email, password}` (email **ou** username accepté) |
| POST | `/auth/refresh` | `{refresh_token}` |
| GET | `/auth/me` | Compte courant |
| PATCH | `/auth/me` | `{full_name?, email?, username?}` |
| POST | `/auth/change-password` | `{current_password, new_password}` |

### 3.3 Profils

| Méthode | Route | Notes |
|---|---|---|
| GET | `/profiles` | Liste des profils du compte |
| POST | `/profiles` | `{name, avatar?, is_kids?, is_default?, language?, pin?, preferences?}` |
| PATCH | `/profiles/{id}` | Champs partiels |
| DELETE | `/profiles/{id}` | Au moins un profil requis |

### 3.4 Catalogue & chaînes

| Méthode | Route | Notes |
|---|---|---|
| GET | `/channels` | Voir filtres ci-dessous |
| GET | `/channels/ids` | Liste légère (cache hors-ligne) |
| GET | `/channels/{id}` | Détail + `stream_url` |
| PATCH | `/channels/{id}` | `{name?, logo?, category_slug?, language_code?, is_active?, priority?, tvg_id?}` |
| DELETE | `/channels/{id}` | Suppression |
| POST | `/channels/{id}/refresh` | Test HTTP + analyse du manifeste |
| GET | `/channels/{id}/play` | Descripteur de lecture (`proxy=true` par défaut) |
| PUT | `/channels/{id}/keys` | `{kid, key}` (hex) |
| DELETE | `/channels/{id}/keys/{kid}` | Retire une clé |
| GET | `/channels/{id}/epg` | `{current, next}` avec progression |

**Filtres de `/channels`** : `q`, `category` (slug ou id), `language` (code ou id), `bouquet` (id/slug/nom),
`provider`, `playlist`, `stream_type`, `status`, `encrypted` (bool), `radio` (bool), `favorites_only` (bool),
+ pagination et tri.

Exemple :

```bash
curl "http://localhost:8080/api/v1/channels?q=bein&language=ar&category=sport&page_size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Descripteur de lecture** (`GET /channels/{id}/play`) :

```json
{
  "channel_id": "f0a1...",
  "url": "/api/v1/streams/proxy?url=https%3A%2F%2F...&channel_id=f0a1...",
  "direct_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
  "stream_type": "hls",
  "is_encrypted": false,
  "encryption": "none",
  "drm_systems": [],
  "variants": [{ "label": "720p", "bandwidth": 1280000, "resolution": "1280x720" }],
  "subtitles": ["Français"],
  "audio_tracks": [],
  "has_keys": false,
  "key_system": null,
  "clearkey_license": null,
  "message": null
}
```

### 3.5 Filtres et catalogue

| Méthode | Route | Description |
|---|---|---|
| GET | `/catalog/categories` | Catégories |
| GET | `/catalog/languages` | Langues |
| GET | `/catalog/bouquets` | Bouquets |
| GET | `/catalog/facets` | Compteurs par catégorie / langue / bouquet + totaux |
| GET | `/catalog/quick-filters` | Raccourcis (sport, arabe, news…) |

### 3.6 Fournisseurs

| Méthode | Route | Notes |
|---|---|---|
| GET | `/providers` | Liste (mots de passe jamais renvoyés, `has_password`) |
| POST | `/providers` | `{name, kind: m3u\|xtream\|hls\|dash, base_url?, username?, password?, epg_url?, notes?}` |
| GET/PATCH/DELETE | `/providers/{id}` | CRUD |
| POST | `/providers/{id}/test` | Test de connexion Xtream |
| POST | `/providers/xtream/preview?base_url=&username=&password=` | Prévisualisation sans import |

### 3.7 Playlists

| Méthode | Route | Notes |
|---|---|---|
| GET | `/playlists` | Liste |
| POST | `/playlists` | `{source_type: url\|text, url?, content?, name?, provider_id?, replace?}` |
| POST | `/playlists/upload` | `multipart/form-data` : `file`, `name?`, `provider_id?`, `replace` |
| POST | `/playlists/xtream` | `{base_url, username, password, name?, epg?}` |
| POST | `/playlists/{id}/sync` | Re-télécharge et met à jour (`?replace=true`) |
| PATCH/DELETE | `/playlists/{id}` | `{name?, is_active?, auto_sync?}` / suppression |

Réponse d'import :

```json
{
  "playlist": { "id": "…", "name": "…", "channel_count": 4 },
  "total": 4, "created": 4, "updated": 0, "skipped": 0,
  "radios": 1, "encrypted": 0,
  "categories": { "sport": 2, "news": 1, "music": 1 },
  "warnings": [], "epg_urls": ["https://…/epg.xml"], "epg_sources": ["…"]
}
```

### 3.8 EPG

| Méthode | Route | Notes |
|---|---|---|
| GET | `/epg/sources` | Sources |
| POST | `/epg/sources` | `{name?, url, provider_id?}` |
| POST | `/epg/upload` | `multipart/form-data` : `file`, `name?` |
| POST | `/epg/sources/{id}/sync` | Télécharge et remplace les programmes |
| GET | `/epg/sources/{id}/programmes` | Programmes à venir |
| GET | `/epg/guide?hours=24&channel_id=` | Guide TV |
| GET | `/epg/now/{channel_id}` | En cours / suivant |
| DELETE | `/epg/sources/{id}` | Suppression |

Association automatique : `channels.epg_channel_id` → `tvg_id` → nom normalisé (`display-name` XMLTV).

### 3.9 Favoris & historique

| Méthode | Route | Notes |
|---|---|---|
| GET | `/favorites` | Favoris du profil actif |
| POST | `/favorites` | `{channel_id}` (idempotent) |
| DELETE | `/favorites/{channel_id}` | Retrait |
| PUT | `/favorites/sync` | `[{channel_id}, …]` remplace la liste |
| GET | `/history?limit=` | Historique |
| POST | `/history` | `{channel_id, position_seconds, duration_seconds?, device?}` |
| GET | `/history/continue` | Reprise (dédupliquée par chaîne) |
| GET | `/history/recent` | Dernières chaînes |
| DELETE | `/history/{id}` / `/history` | Une entrée / tout l'historique |

### 3.10 Scan

| Méthode | Route | Notes |
|---|---|---|
| POST | `/scan` | `{playlist_id?, provider_id?, channel_ids?, probe=true}` → 202 + job |
| GET | `/scan/jobs?limit=` | Historique |
| GET | `/scan/jobs/{id}` | Progression, compteurs, logs |
| GET | `/scan/latest` | Dernier job ou `null` |

Le job s'exécute en arrière-plan. Sondage recommandé toutes les 1,5 s pendant `status ∈ {queued,running}`.

### 3.11 Statistiques & réglages

| Méthode | Route | Notes |
|---|---|---|
| GET | `/stats/dashboard` | Compteurs, répartitions, activité, historique, dernier scan |
| GET | `/stats/activity?limit=` | Journal d'activité |
| GET | `/settings` | Réglages (utilisateur + globaux) |
| PUT | `/settings` | `{key, value}` (upsert) |
| DELETE | `/settings/{key}` | Suppression |

### 3.12 Lecture & proxy

| Méthode | Route | Notes |
|---|---|---|
| GET | `/streams/proxy?url=&channel_id=` | Relaie manifestes (réécrits), segments, sous-titres |
| GET | `/streams/key?uri=&channel_id=&kid=` | Sert une clé ClearKey/AES-128 |

* `channel_id` restreint les hôtes autorisés au domaine du flux (anti-relais ouvert, anti-SSRF).
* Les manifestes HLS sont réécrits : variantes, segments, `#EXT-X-KEY`, `#EXT-X-MAP`, sous-titres.
* Les manifestes DASH reçoivent une `<BaseURL>` absolue.
* Aucun déchiffrement n'est effectué côté serveur : les clés détenues par l'utilisateur sont relayées.

### 3.13 Administration

| Méthode | Route | Notes |
|---|---|---|
| GET | `/admin/users` | Liste des comptes (admin) |
| PATCH | `/admin/users/{id}` | `{role?, is_active?}` |

---

## 4. Exemples complets

### Importer puis lire

```bash
TOKEN=...   # voir §1

# 1) import
curl -s -X POST localhost:8080/api/v1/playlists \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"source_type":"text","content":"#EXTM3U\n#EXTINF:-1 group-title=\"Sport\",Demo\nhttps://example.com/live.m3u8"}' | jq

# 2) recherche
CH=$(curl -s "localhost:8080/api/v1/channels?q=Demo" -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].id')

# 3) lecture
curl -s "localhost:8080/api/v1/channels/$CH/play" -H "Authorization: Bearer $TOKEN" | jq -r .url
```

### EPG de bout en bout

```bash
curl -X POST localhost:8080/api/v1/epg/sources -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"Mon EPG","url":"https://exemple.com/epg.xml"}'
SRC=$(curl -s localhost:8080/api/v1/epg/sources -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')
curl -X POST "localhost:8080/api/v1/epg/sources/$SRC/sync" -H "Authorization: Bearer $TOKEN" | jq
curl "localhost:8080/api/v1/epg/guide?hours=12" -H "Authorization: Bearer $TOKEN" | jq '.[0:3]'
```

### Clé ClearKey

```bash
curl -X PUT localhost:8080/api/v1/channels/$CH/keys \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"kid":"0123456789abcdef0123456789abcdef","key":"fedcba9876543210fedcba9876543210"}'
```

---

## 5. Clients

* **Web** : `web/src/api/endpoints.ts` (TypeScript, typé).
* **Flutter** : `mobile/lib/services/api_service.dart`.
* **Postman/Insomnia** : importez `http://localhost:8080/openapi.json`.

## 6. Limites & bonnes pratiques

| Limite | Valeur |
|---|---|
| Débit API | 300 req/min/client (`RATE_LIMIT_REQUESTS`) |
| Login | 5 req/min via Nginx |
| Corps de requête | 64 Mo (Nginx), 40 Mo (playlist applicative) |
| Timeout import | 25 s (`HTTP_TIMEOUT_SECONDS`) |
| Scan | 5 000 chaînes max par job, 8 requêtes parallèles |

Pour les listes volumineuses, paginez (`page_size ≤ 200`) et utilisez `/channels/ids` pour les caches locaux.
