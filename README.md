<div align="center">

# 📺 PrimeTV

**Plateforme IPTV moderne, performante et 100 % open source.**
Playlists M3U/M3U8 · Xtream Codes · HLS/DASH · EPG XMLTV · 8 catégories · 5 langues · multi-profils

[![Licence MIT](https://img.shields.io/badge/licence-MIT-3382fb.svg)](LICENSE)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](backend/)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-61dafb.svg)](web/)
[![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8.svg)](public/sw.js)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](docker-compose.yml)
[![Tests](https://img.shields.io/badge/tests-backend%2033%20%2B%20frontend%2012-22c55e.svg)](#-tests)

</div>

---

> ## ⚖️ Avertissement légal — à lire avant utilisation
>
> **PrimeTV est un lecteur.** Le projet ne fournit, n'héberge et ne distribue **aucune chaîne, aucun flux,
> aucune playlist et aucune clé de déchiffrement**.
>
> * N'importez que des sources que vous êtes **autorisé** à regarder (chaînes gratuites, your own subscription,
>   contenus libres de droits).
> * PrimeTV **ne contourne aucun système de protection** : les flux Widevine / PlayReady / FairPlay sont
>   détectés, signalés et **refusés à la lecture**. Aucun outil de cracking, aucun serveur de clés pirate
>   n'est inclus ni ne sera accepté en contribution.
> * Les clés ClearKey / AES-128 peuvent être saisies **uniquement** pour du contenu que vous détenez
>   légitimement ; elles restent sous votre responsabilité.
> * Le catalogue de démonstration pointe vers des flux de test publics (Apple, Mux, Akamai, SomaFM).
>
> Vous êtes seul responsable de l'usage que vous faites de ce logiciel.

---

## ✨ Fonctionnalités

| Domaine | Détail |
|---|---|
| **Imports** | URL M3U / M3U8 / HLS, fichier `.m3u`, contenu collé, manifeste DASH `.mpd`, portail **Xtream Codes** (player_api.php) |
| **EPG** | Import **XMLTV** par URL ou fichier, association automatique (`tvg-id` → `epg_channel_id` → nom normalisé), guide TV + « en cours / à suivre » |
| **Lecture** | **HLS** (hls.js), **DASH** (dash.js), **MP4**, **MPEG-TS**, radios ; qualité auto ou manuelle, sous-titres, **Picture in Picture**, plein écran, proxy CORS |
| **Catalogue** | Classification automatique : **Sport, News, Movies, Kids, Music, Religion, Documentary, Entertainment, Culture, Local, Adult** ; langues **AR, FR, EN, TR, ES**, + DE, IT, PT, NL, RU, HI, UR, FA, KU, ZH |
| **Priorisation** | Score de mise en avant : **sport (+40)** et **arabe (+35)** en tête, puis news, français, EPG ; radio et adultes pénalisés |
| **Recherche** | Plein texte (nom, groupe, TVG, arabe sans diacritiques), filtres catégorie / langue / bouquet / fournisseur / playlist / type / statut / chiffrement / radios, tri et pagination |
| **Profils** | Multi-profils par compte (enfant, invité), favoris et historique **isolés par profil**, code PIN |
| **Favoris / Historique** | Ajout/suppression, synchronisation multi-appareils, **continuer la lecture**, dernières chaînes |
| **Scan** | Bouton **scan/actualisation** : test HTTP concurrent des flux, analyse des manifestes, détection **AES-128 / ClearKey / DRM**, mise à jour qualité, statut et logos |
| **Chaînes chiffrées** | Badge explicite, clés **ClearKey** saisies par l'utilisateur, proxy de clés ; DRM signalé et bloqué (voir avertissement) |
| **Interface** | React 18 + TypeScript + Tailwind, **dark/light**, responsive (téléphone → 4K), animations, squelettes de chargement |
| **Web app / PWA** | **Application web unique et installable** : manifeste, service worker (mode hors ligne), raccourcis, icônes, ajout à l'écran d'accueil Android/iOS et installation desktop — aucun store, aucun APK |
| **Backend** | **FastAPI** (Python 3.11+), SQLAlchemy 2, PostgreSQL 16, Redis 7, JWT, rate limiting, validation Pydantic, logs JSON |
| **Docs** | **Swagger UI** (`/docs`), ReDoc, OpenAPI JSON, 9 guides Markdown |
| **Ops** | Docker Compose, Nginx (HTTP/2, gzip, TLS), Traefik (Let's Encrypt), healthchecks, scripts install/update/backup/restore, CI GitHub Actions |

---

## 🏗️ Architecture

```
                        ┌──────────────────────────────────────────────┐
                        │                 Navigateur                  │
                        │   React 18 + TS + Vite + Tailwind (SPA)     │
                        │   hls.js (HLS) · dash.js (DASH)             │
                        └──────────────┬───────────────────────────────┘
                                       │ HTTPS / WSS
                        ┌──────────────▼───────────────────────────────┐
                        │   Nginx (HTTP/2, gzip, TLS) — ou Traefik     │
                        └───────┬───────────────────────────┬──────────┘
                                │ /  (SPA + PWA)            │ /api /docs
                  ┌─────────────▼───────────┐     ┌─────────▼──────────────┐
                  │  React SPA + service     │     │  FastAPI (Gunicorn)    │
                  │  worker (PWA installable)│     │  JWT · Rate-limit      │
                  └─────────────────────────┘     │  Services :            │
                                                  │   parseur M3U/XMLTV    │
                                                  │   classifieur          │
                                                  │   scanner HLS/DASH     │
                                                  │   proxy de lecture     │
                                                  └────┬───────────┬───────┘
                                                       │           │
                                        ┌──────────────▼──┐   ┌────▼─────────────┐
                                        │  PostgreSQL 16  │   │    Redis 7       │
                                        │  (catalogue,    │   │  cache + rate    │
                                        │   EPG, profils) │   │  limiting        │
                                        └─────────────────┘   └──────────────────┘
```

**Flux d'import** : source (URL/fichier/Xtream) → téléchargement borné (anti-SSRF) → parseur tolérant →
classifieur (catégorie, langue, qualité, priorité, bouquets) → upsert idempotent (clé = hash de l'URL) →
EPG détecté → sources XMLTV enregistrées.

**Flux de lecture** : `/channels/{id}/play` → descripteur (URL proxifiée, type, variantes, DRM, clés) →
lecteur web (hls.js / dash.js / <video>) → proxy `/streams/proxy` qui réécrit les manifestes et relaie
segments + clés → reprise de lecture enregistrée dans l'historique du profil.

---

## 🚀 Démarrage rapide

### Prérequis
* Docker ≥ 24 et Docker Compose v2 — **ou** Python 3.11+ et Node 20+ pour le développement local.
* Un navigateur moderne (Chrome/Edge/Firefox/Safari) : l'application est **100 % web**, installable en PWA.

### Installation en une commande

```bash
git clone https://github.com/HamdiSouissi/primeTV.git
cd primeTV
./scripts/install.sh            # secrets générés, images construites, services démarrés
```

| Service | URL |
|---|---|
| Interface web | http://localhost:8080 |
| Installation PWA | bouton **Installer** dans la barre supérieure (ou menu du navigateur) |
| Documentation API (Swagger) | http://localhost:8080/docs |
| Healthcheck | http://localhost:8080/healthz |

```bash
# avec TLS automatique (Traefik + Let's Encrypt, nécessite un domaine)
TRAEFIK_DOMAIN=tv.example.com TRAEFIK_ACME_EMAIL=vous@example.com \
  ./scripts/install.sh --tls
```

**Identifiants initiaux** : `admin@primetv.io` / `PrimeTV#2026` → **changez-les immédiatement**
(Réglages → Sécurité). Le catalogue de démonstration contient 10 flux publics de test
(désactivable avec `./scripts/install.sh --demo-off`).

### Développement local (sans Docker)

```bash
./scripts/dev.sh
# API   : http://localhost:8000/docs  (SQLite, rechargement auto)
# Web   : http://localhost:5173
```

### Installer l'application (PWA)

PrimeTV est une **application web unique** : elle s'installe depuis le navigateur, sans store.

| Plateforme | Procédure |
|---|---|
| **Android** (Chrome, Edge, Samsung Internet) | ouvrir l'URL → bandeau **Installer** (ou ⋮ → « Installer l'application ») |
| **iOS / iPadOS** (Safari) | Partager → **Sur l'écran d'accueil** |
| **Windows / macOS / Linux** (Chrome, Edge) | icône **Installer** dans la barre d'adresse, ou bouton **Installer** de PrimeTV |
| **Sans installation** | l'application fonctionne directement dans l'onglet |

Une fois installée : plein écran sans barre d'adresse, icône dédiée, raccourcis « Chaînes / Sport /
Guide / Favoris », et page « hors connexion » si le réseau tombe. Détails : **[docs/PWA.md](docs/PWA.md)**.

> L'application ne contient aucun flux : elle se connecte à l'API PrimeTV (même origine).

---

## 🗂️ Arborescence

```
primeTV/
├── backend/                      # API FastAPI
│   ├── app/
│   │   ├── main.py               # application, middlewares, OpenAPI
│   │   ├── core/                 # config, sécurité JWT, cache, logs, erreurs, pagination, proxy HTTP
│   │   ├── db/                   # base déclarative, mixins UTC, session SQLAlchemy
│   │   ├── models/               # User, Profile, Provider, Playlist, Channel, Category, Language,
│   │   │                         # Bouquet, EpgSource, EpgProgramme, Favorite, History, ScanJob, Setting
│   │   ├── schemas/              # schémas Pydantic (validation + OpenAPI)
│   │   ├── api/v1/               # auth, catalog, channels, providers, playlists, epg, favorites,
│   │   │                         # history, scan, stats, settings, streams, system
│   │   ├── services/             # m3u, xmltv, xtream, classifier, streams (DRM), importer,
│   │   │                         # scanner, proxy, seed
│   │   └── utils/
│   ├── tests/                    # 33 tests (unitaires + intégration API)
│   ├── Dockerfile & docker-entrypoint.sh
│   └── requirements.txt / pyproject.toml
├── web/                          # Frontend React + TS + Vite + Tailwind
│   ├── src/{api,components,hooks,lib,pages,store,styles,test}
│   ├── public/                   # manifeste PWA, service worker, icônes, page hors ligne
│   ├── scripts/generate-icons.py # génération des icônes PWA (sans dépendance)
│   ├── Dockerfile & nginx.conf
│   └── package.json / vite.config.ts / tailwind.config.js
├── docker/
│   ├── nginx/                    # reverse proxy d'entrée (HTTP/2, TLS auto-signé)
│   ├── traefik/                  # configuration dynamique + Let's Encrypt
│   └── postgres/init.sql         # extensions PostgreSQL
├── scripts/                      # install, update, backup, restore, dev, healthcheck, tests, certificat
├── tests/api/smoke.sh            # tests API bout-en-bout (curl)
├── docs/                         # 11 guides (installation, API, admin, sécurité…)
├── examples/                     # playlist M3U + EPG XMLTV de démonstration
├── .github/workflows/ci.yml      # CI (lint, tests, build, docker)
├── docker-compose.yml
├── .env.example
├── CONTRIBUTING.md               # guide de contribution
├── .gitattributes                # fins de ligne LF forcées (Windows/CRLF)
├── LICENSE (MIT)
├── Makefile
└── README.md
```

---

## 🔌 API REST (résumé)

Documentation interactive : **`/docs`** (Swagger UI) et **`/redoc`**. OpenAPI : `/openapi.json`.

```bash
# Connexion
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@primetv.io","password":"PrimeTV#2026"}' | jq -r .access_token)

# Importer une playlist
curl -X POST http://localhost:8080/api/v1/playlists \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"source_type":"url","url":"https://exemple.com/playlist.m3u"}'

# Rechercher des chaînes sportives arabes
curl "http://localhost:8080/api/v1/channels?category=sport&language=ar&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# Lancer un scan du catalogue
curl -X POST http://localhost:8080/api/v1/scan \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"probe":true}'
```

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/auth/register` · `/auth/login` · `/auth/refresh` | Comptes et jetons JWT |
| `GET/PATCH` | `/auth/me` | Profil du compte |
| `GET/POST/PATCH/DELETE` | `/profiles` | Multi-profils |
| `GET` | `/channels` | Recherche paginée, filtres, tri prioritaire |
| `GET` | `/channels/{id}` · `/channels/{id}/play` · `/channels/{id}/epg` | Détail, descripteur de lecture, EPG |
| `PUT/DELETE` | `/channels/{id}/keys` | Clés ClearKey fournies par l'utilisateur |
| `POST` | `/channels/{id}/refresh` | Test unitaire d'un flux |
| `GET/POST/PATCH/DELETE` | `/playlists` (+ `/upload`, `/xtream`, `/{id}/sync`) | Imports M3U, fichier, Xtream |
| `GET/POST/PATCH/DELETE` | `/providers` (+ `/xtream/preview`, `/{id}/test`) | Fournisseurs autorisés |
| `GET/POST/DELETE` | `/epg/sources` (+ `/upload`, `/guide`, `/{id}/sync`) | EPG XMLTV |
| `GET/POST/PUT/DELETE` | `/favorites`, `/history` | Favoris, historique, reprise |
| `POST/GET` | `/scan`, `/scan/jobs`, `/scan/latest` | Scan & détection du chiffrement |
| `GET` | `/stats/dashboard`, `/catalog/facets`, `/catalog/quick-filters` | Tableau de bord et filtres |
| `GET` | `/streams/proxy`, `/streams/key` | Proxy HLS/DASH et distribution de clés |

Détails, codes d'erreur et exemples complets : **[docs/API.md](docs/API.md)**.

---

## 🧠 Classification & priorisation

Le classifieur (`backend/app/services/classifier.py`) est **explicite, déterministe et extensible** :
aucun modèle externe, aucun service propriétaire.

1. **Catégorie** — mots-clés multilingues (latin + arabe) sur le nom et `group-title` ; score par correspondance
   de mot entier ; `adult` prioritaire s'il est détecté.
2. **Langue** — indices explicites (`tvg-language`, `tvg-country`), script arabe, indices français, pays, heuristiques.
3. **Qualité** — `8K`, `4K`, `FHD`, `HD`, `SD` (nom, groupe, variantes HLS).
4. **Priorité** — sport `+40`, arabe `+35`, news `+20`, français `+10`, EPG `+2`, radio `-5`, adult `-100`.
   Le tri par défaut est `priority DESC, name ASC` → **sport et chaînes arabes en tête**.
5. **Bouquets** — `group-title` d'origine + nom du fournisseur.

Pour ajouter une catégorie : une entrée dans `CATEGORY_RULES`, redémarrez, elle apparaît dans l'UI et l'API.

---

## 🔐 Chaînes chiffrées : ce que fait PrimeTV (et ce qu'il ne fait pas)

| Situation | Comportement |
|---|---|
| Flux libre | Lecture directe, statut `active` |
| **AES-128 / ClearKey** avec clé **fournie par l'utilisateur** | Clé stockée (par chaîne), proxy `/streams/key` la relaie au lecteur, badge « clés actives » |
| **AES-128 / ClearKey** sans clé | Badge « chiffrée », invitation à saisir une clé si vous en détenez une |
| **Widevine / PlayReady / FairPlay** | Détecté (`drm_systems`), **lecture bloquée**, message explicite : aucun contournement |
| Manifeste illisible | Statut `offline`, log dans le job de scan |

La « recherche de sources déchiffrées » demandée dans le cahier des charges est donc traitée de manière
**légale et technique** : détection automatique + gestion de vos propres clés + documentation pour ajouter
des sources libres. Voir [docs/SECURITY.md](docs/SECURITY.md#drm-et-legalite).

---

## ⚙️ Configuration

Tout est piloté par variables d'environnement (`.env`). Les plus importantes :

| Variable | Défaut | Rôle |
|---|---|---|
| `SECRET_KEY` | — | Signature JWT + chiffrement des identifiants (obligatoire en prod) |
| `DATABASE_URL` | SQLite local | `postgresql+psycopg://user:pass@postgres:5432/primetv` |
| `REDIS_URL` | vide (cache mémoire) | `redis://redis:6379/0` |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | URL publique (OpenAPI, liens) |
| `ALLOW_REGISTRATION` | `true` | Inscriptions ouvertes |
| `RATE_LIMIT_REQUESTS` | `300` / 60 s | Limite par client |
| `SEED_DEMO_DATA` | `true` | Catalogue de démonstration |
| `PRIORITY_SPORT` / `PRIORITY_ARABIC` | `40` / `35` | Mise en avant |
| `PROBE_CONCURRENCY` | `8` | Parallélisme du scan |
| `ALLOW_PRIVATE_STREAM_HOSTS` | `false` | Autoriser les flux LAN (SSRF) |

Table complète commentée : **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)**.

---

## 🧪 Tests

```bash
./scripts/test-all.sh          # lint + tests backend + typecheck + tests + build frontend + smoke API
```

| Suite | Outil | Contenu |
|---|---|---|
| Backend unitaire | pytest | parseur M3U/M3U8/HLS, XMLTV, classifieur, analyse DRM HLS/DASH |
| Backend intégration | pytest + TestClient | auth/profils, imports, recherche/filtres/priorité, favoris, historique, EPG, scan, stats, proxy |
| Frontend | Vitest + Testing Library | cartes de chaînes, lecteur (blocage DRM), formatage, PWA |
| API bout-en-bout | bash + curl | parcours complet sur une instance démarrée |
| CI | GitHub Actions | lint, tests, build web, smoke API, validation PWA & compose |

```bash
cd backend && .venv/bin/python -m pytest -q          # 33 tests
cd web && npm run test                               # 12 tests
```

---

## 🛠️ Scripts

| Script | Rôle |
|---|---|
| `scripts/install.sh` | Installation complète (secrets, certificat, build, démarrage) |
| `scripts/update.sh` | Sauvegarde + `git pull` + rebuild + redémarrage |
| `scripts/backup.sh` | Dump PostgreSQL compressé + rotation (`KEEP_DAYS`) |
| `scripts/restore.sh` | Restauration (`--latest` ou fichier) avec confirmation |
| `scripts/dev.sh` | API + Vite en local |
| `scripts/healthcheck.sh` | Vérifie API, docs, web, manifeste PWA, conteneurs |
| `scripts/fix-line-endings.sh` | Convertit les CRLF en LF (checkout Windows) et valide les scripts |
| `scripts/test-all.sh` | Toute la suite de tests |
| `scripts/gen-self-signed-cert.sh` | Certificat TLS local |
| `make help` | Raccourcis Makefile |

---

## 📚 Documentation

| Document | Public |
|---|---|
| [Installation (Linux / Windows / Docker)](docs/INSTALL.md) | Tous |
| [Configuration & variables](docs/CONFIGURATION.md) | Admin / dev |
| [Documentation API](docs/API.md) | Dev / intégrateurs |
| [Guide utilisateur](docs/USER_GUIDE.md) | Utilisateurs |
| [Guide administrateur](docs/ADMIN_GUIDE.md) | Exploitants |
| [Guide développeur](docs/DEVELOPER_GUIDE.md) | Contributeurs |
| [Déploiement & production](docs/DEPLOYMENT.md) | DevOps |
| [Application web & PWA](docs/PWA.md) | Tous |
| [Sécurité & légalité](docs/SECURITY.md) | Tous |
| [Architecture & schéma BDD](docs/ARCHITECTURE.md) | Dev |
| [Dépannage](docs/TROUBLESHOOTING.md) | Tous |

---

## 🤝 Contribuer

Les contributions sont bienvenues (code, docs, traductions). Voir [CONTRIBUTING.md](CONTRIBUTING.md).
Sont **refusés** : contournement de DRM, listes de flux piratés, dépendances propriétaires.

```bash
git checkout -b feat/ma-fonctionnalite
./scripts/test-all.sh
git commit -m "feat: ma fonctionnalité"
```

## 📄 Licence

[MIT](LICENSE) — dépendances sous licences MIT, Apache-2.0, BSD et LGPL (driver `psycopg` non modifié).
Aucune dépendance propriétaire.

<div align="center"><sub>Fait avec ❤️ pour une télévision libre et maîtrisée.</sub></div>
