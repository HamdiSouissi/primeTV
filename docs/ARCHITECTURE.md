# Architecture technique

## 1. Vue d'ensemble

```
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│  React SPA + PWA      │   │  Clients API tiers    │   │  Swagger / Postman    │
│  Vite · TS · Tailwind │   │  (mobile, scripts)    │   │  (clients API)        │
└──────────┬────────────┘   └──────────┬────────────┘   └──────────┬────────────┘
           │  HTTPS (même origine)     │                            │
           └───────────────┬───────────┴────────────────────────────┘
                           ▼
                ┌──────────────────────────┐
                │ Nginx (ou Traefik)       │
                │ HTTP/2 · gzip · TLS      │
                │ rate limit · /api proxy  │
                └────────────┬─────────────┘
                             ▼
                ┌──────────────────────────┐
                │ FastAPI + Gunicorn       │
                │ Uvicorn workers          │
                ├──────────────────────────┤
                │ api/v1 (routers)         │
                │ services (métier)        │
                │ models (SQLAlchemy 2)    │
                └───────┬──────────┬───────┘
                        ▼          ▼
              ┌──────────────┐  ┌──────────────┐
              │ PostgreSQL16 │  │ Redis 7      │
              │ données      │  │ cache/ratelim│
              └──────────────┘  └──────────────┘
                        │
                        ▼ flux entrants (import) / sortants (proxy)
              ┌──────────────────────────────────────┐
              │ Fournisseurs : M3U · Xtream · HLS ·  │
              │ DASH · XMLTV                         │
              └──────────────────────────────────────┘
```

## 2. Choix techniques

| Décision | Justification |
|---|---|
| **FastAPI** plutôt que Go/Gin | Typage Pydantic → OpenAPI gratuit et fiable, écosystème Python pour le parsing XML/HTTP, tests rapides. Le cahier des charges autorisait les deux. |
| **SQLAlchemy 2 + PostgreSQL** | Modèle relationnel clair, index adaptés, portabilité SQLite pour les tests. |
| **Redis optionnel** | Dégradation gracieuse en cache mémoire : l'installation fonctionne sans Redis. |
| **UUID CHAR(36)** | Portable SQLite/PostgreSQL, pas de fuite d'énumération d'identifiants. |
| **Proxy de lecture** | Corrige CORS, réécrit les manifestes (segments/clés/sous-titres), évite d'exposer des tokens au navigateur. |
| **hls.js + dash.js** | Lecteurs libres, matures, qualité manuelle et sous-titres. |
| **PWA** (service worker + manifeste) | Une seule base de code web ; installation native-like, cache de l'app shell et page hors ligne sans store ni APK. |
| **TailwindCSS** | Design system cohérent, dark mode natif, aucun CSS runtime propriétaire. |

## 3. Pipeline d'import

```
URL / fichier / Xtream / texte
        │
        ▼
 validate_remote_url (anti-SSRF) ── refus si schéma invalide ou IP privée
        │
        ▼
 fetch_text (plafond MAX_PLAYLIST_BYTES, timeout 25 s, décodage utf-8/latin-1)
        │
        ▼
 parse_m3u / fetch_xtream / parse_hls_master
  ├─ attributs #EXTINF (tvg-id, group-title, logo…)
  ├─ #KODIPROP license_type → indice de chiffrement
  ├─ EPG (url-tvg / x-tvg-url)
  └─ type de flux par extension
        │
        ▼
 classify()  ── catégorie, langue, qualité, priorité, bouquets, radio
        │
        ▼
 upsert chaîne (clé sha256(url)) ── favoris/historique préservés
        │
        ▼
 save_epg_urls() ── sources EPG créées (statut pending)
        │
        ▼
 ActivityLog + réponse ImportResult (compteurs, warnings)
```

## 4. Pipeline de lecture

```
GET /channels/{id}/play
  └─ descripteur : url proxy (relative), direct_url, type, variantes, DRM, clés

Navigateur :
  hls.js ─► GET /streams/proxy?url=…/master.m3u8
              └─ réécriture : variantes → proxy, #EXT-X-KEY → /streams/key,
                 #EXT-X-MAP/#EXT-X-MEDIA → proxy
  hls.js ─► GET /streams/proxy?url=…/segment.ts (streaming direct)
  hls.js ─► GET /streams/key?uri=…           (clé utilisateur ou distante autorisée)
```

Contrôles de sécurité du proxy :
1. schéma http/https obligatoire ;
2. `channel_id` → hôte du flux ; sinon `validate_remote_url` ;
3. comparaison de domaine (même enregistrement), sinon **403** ;
4. manifestes limités à 512 Ko en lecture d'analyse (le proxy lui-même streame).

## 5. Pipeline de scan

```
POST /scan → ScanJob(queued) → BackgroundTask
   │
   ▼
sélection des chaînes (playlist / provider / ids / catalogue, ≤ SCAN_MAX_CHANNELS)
   │
   ▼
ThreadPoolExecutor(PROBE_CONCURRENCY) : GET Range: bytes=0-65535
   ├─ statut HTTP, content-type
   ├─ manifeste HLS → analyze_hls (clés, variantes, sous-titres)
   ├─ manifeste DASH → analyze_dash (ContentProtection, représentations)
   └─ erreurs réseau → log tronqué
   │
   ▼
apply_probe() par chaîne : status, http_status, encryption, drm_systems,
variants, qualité déduite de la meilleure variante
   │
   ▼
commit par lots (50) + progression + logs (job) + ActivityLog
```

## 6. Modèle de données (relations)

```
users 1──n profiles
users 1──n providers 1──n playlists 1──n channels
providers 1──n bouquets
categories 1──n channels      languages 1──n channels
channels n──n bouquets (channel_bouquets)
playlists 1──n epg_sources?   (indirect : users/providers)
epg_sources 1──n epg_programmes n──1 channels (association par xmltv_id)
profiles 1──n favorites n──1 channels
profiles 1──n history   n──1 channels
users 1──n scan_jobs
users 1──n settings (ou global si user_id NULL)
users 1──n activity_logs
```

Index principaux :

* `channels(priority, name)` → tri par défaut ;
* `channels(category_id, language_id, is_radio)` → filtres combinés ;
* `channels(playlist_id, stream_key)` unicité d'import ;
* `channels(epg_channel_id)`, `epg_programmes(xmltv_id, start_at)`, `(start_at, stop_at)` → guide ;
* `history(profile_id, watched_at)`, `favorites(profile_id, channel_id)` unicité.

## 7. Priorisation de l'interface

`compute_priority()` (settings) :

| Critère | Points |
|---|---|
| Sport | +40 (`PRIORITY_SPORT`) |
| Arabe | +35 (`PRIORITY_ARABIC`) |
| News | +20 |
| Français | +10 |
| EPG associé | +2 |
| Radio | −5 |
| Adult | −100 |

Tri par défaut : `priority DESC, name ASC`. Les rails du tableau de bord interrogent directement
`category=sport` et `language=ar`. Modifiable sans code via `.env`.

## 8. Extensibilité

| Besoin | Point d'extension |
|---|---|
| Nouvelle catégorie / langue | `CATEGORY_RULES` / `LANGUAGE_RULES` |
| Nouveau format de playlist | `services/<format>.py` → `ParsedPlaylist` → `import_playlist_content` |
| Nouveau type de flux | `services/streams.detect_stream_type` + `VideoPlayer` |
| Nouvelle source EPG | `services/xmltv.parse_xmltv` (formats XMLTV exotiques) |
| Nouveau provider d'authentification | `api/deps.get_current_user` (OIDC, etc.) |
| Nouveau client | tirer parti d'OpenAPI (`/openapi.json`) |
