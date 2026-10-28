# Dépannage

## Démarrage

### `POSTGRES_PASSWORD est requis` / `env file .env not found`
`.env` manquant. `cp .env.example .env` puis renseignez `POSTGRES_PASSWORD` et `SECRET_KEY`
(ou relancez `./scripts/install.sh` qui les génère).

### `port is already allocated`
Un service écoute déjà sur 8080/8443. Changez dans `.env` :

```env
HTTP_PORT=8081
HTTPS_PORT=8444
```

puis `docker compose up -d`.

### Backend `unhealthy`, logs `could not connect to server`
PostgreSQL n'est pas prêt ou les identifiants diffèrent entre `POSTGRES_*` et `DATABASE_URL`.
Alignez-les, puis :

```bash
docker compose down
docker compose up -d
```

### `SECRET_KEY doit contenir au moins 16 caractères`
Valeur trop courte : `openssl rand -base64 48`.

### Nginx : `/docker-entrypoint.d/10-primetv-cert.sh: not found`
### Backend : `env: use -[v]S to pass options in shebang lines`

**Cause** : fins de ligne **CRLF** (checkout Git sous Windows). Le noyau lit le shebang
avec un retour chariot (`#!/bin/sh\r`) et ne trouve pas l'interpréteur. Symptômes jumeaux :
nginx redémarre en boucle, le backend ne démarre jamais.

**Correctif immédiat** (sans re-cloner) :

```bash
./scripts/fix-line-endings.sh                # convertit CRLF → LF
git config core.autocrlf input               # évite la récidive
docker compose build --no-cache backend nginx web
docker compose up -d
```

Le dépôt contient un `.gitattributes` (`* text=auto eol=lf`) : après
`git add --renormalize . && git commit`, un clone neuf est correct.
Les images `backend` et `nginx` retirent de toute façon les `\r` à la construction
(`sed -i 's/\r$//'`), la reconstruction suffit donc dans la majorité des cas.

Sous **PowerShell** (sans Git Bash), équivalent :

```powershell
Get-ChildItem -Recurse -File -Include *.sh,*.conf,Dockerfile,docker-entrypoint.sh |
  ForEach-Object {
    $c = Get-Content $_.FullName -Raw
    if ($c -match "`r`n") { Set-Content -NoNewline -Encoding utf8 $_.FullName ($c -replace "`r`n", "`n") }
  }
```

Vérification :

```bash
./scripts/fix-line-endings.sh --check        # code 0 = tout est en LF
docker compose logs --tail=30 nginx backend
```

### Build nginx : `host not found in upstream "backend:8000"`
Le `nginx -t` exécuté **pendant la construction de l'image** tente de résoudre les
amonts Docker Compose — impossibles à résoudre hors du réseau `primetv_net`.

Depuis la version 1.0.1 de `docker/nginx/Dockerfile`, la validation porte sur une
copie de la configuration où `backend:8000` et `web:80` sont remplacés par des
adresses locales : la syntaxe, les `location`, les modules et les certificats sont
vérifiés, sans dépendre du DNS Docker. Si vous voyez encore ce message :

```bash
git pull
docker compose build --no-cache nginx
docker compose up -d
```

### `502 Bad Gateway` sur `/api/v1/config` (l'interface ne peut pas se connecter)

Symptôme typique dans la console du navigateur :

```
GET http://localhost:8080/api/v1/config 502 (Bad Gateway)
```

Le proxy Nginx fonctionne (la page s'affiche) mais il ne joint pas le conteneur
`backend`. PrimeTV 1.0.2 affiche désormais une **bannière rouge explicite** avec
la commande à lancer ; voici la marche à suivre complète.

```bash
./scripts/diagnose.sh          # enchaîne les 6 vérifications et pointe la cause
```

Causes, par ordre de fréquence :

| # | Cause | Vérification | Correctif |
|---|---|---|---|
| 1 | Backend arrêté / en boucle de redémarrage (erreur de base, import) | `docker compose ps` (`Restarting`, `unhealthy`) et `docker compose logs --tail=80 backend` | corriger l'erreur affichée, puis `docker compose up -d --force-recreate backend` |
| 2 | **Backend recréé → nouvelle IP**, Nginx gardait l'ancienne | `docker compose exec nginx getent hosts backend` | `docker compose restart nginx` — **corrigé en 1.0.2** (résolution DNS dynamique via `resolver 127.0.0.11 valid=10s`) |
| 3 | Mot de passe PostgreSQL incohérent entre `POSTGRES_PASSWORD` et `DATABASE_URL` | `docker compose logs backend` → `password authentication failed` | aligner les deux valeurs dans `.env`, `docker compose up -d --force-recreate backend` |
| 4 | Base pas encore initialisée (premier démarrage) | `docker compose ps` → `postgres starting` | attendre ~30 s ; le point d'entrée attend la base (`DB_WAIT_SECONDS=60`) |
| 5 | Variable `PORT` définie dans `.env` → gunicorn n'écoute pas sur 8000 | `grep '^PORT=' .env` | supprimer la ligne, `docker compose up -d --force-recreate backend` |
| 6 | Conteneurs sur des réseaux différents | `docker compose exec nginx getent hosts backend` vide | `docker compose down && docker compose up -d` |

Commandes de contrôle, dans l'ordre :

```bash
curl -i http://localhost:8080/nginx-health        # 200 → le proxy tourne
curl -i http://localhost:8080/healthz             # 200 → API + base OK
curl -i http://localhost:8080/api/v1/config       # 200 → route publique
docker compose exec nginx curl -i http://backend:8000/healthz   # 200 → réseau Docker OK
docker compose logs --tail=80 backend             # erreur applicative éventuelle
```

Tant que l'API est injoignable, l'interface affiche la bannière « L'API PrimeTV ne
répond pas (502) » avec un bouton **Réessayer** (elle teste `/healthz` puis recharge
si le backend est revenu) : inutile de vider le cache.

### Erreur 502 juste après un `docker compose up -d backend`
Nginx résout le nom `backend` **au démarrage** et conserve l'adresse IP obtenue.
Si le conteneur backend est **recréé** (nouvelle IP), rechargez le proxy :

```bash
docker compose restart nginx
```

`docker compose up -d` recrée nginx automatiquement lorsque sa configuration a changé.
Les dépendances `service_healthy` garantissent par ailleurs que `backend` et `web`
répondent avant le lancement de Nginx.

### Nginx redémarre en boucle (TLS)
Le certificat n'a pas pu être généré. Depuis la version 1.0.1, l'image `nginx` est
construite depuis `docker/nginx/Dockerfile` et **embarque `openssl`** ainsi que le
script de génération ; supprimez les certificats et relancez :

```bash
rm -f docker/nginx/certs/primetv.crt docker/nginx/certs/primetv.key
docker compose up -d --build nginx
docker compose logs nginx | grep primetv
```

La configuration est validée à la construction (`nginx -t`) : une erreur de syntaxe
fait échouer le build, pas le démarrage.

### `/nginx-health` renvoie 200 mais `/healthz` échoue
`/nginx-health` teste **uniquement le proxy** ; `/healthz` teste la pile complète
(API → base de données). Si `/healthz` échoue, inspectez `docker compose logs backend`
et l'état de `postgres`.

### L'interface affiche « Serveur injoignable »
* L'API doit être joignable **via la même origine** : Nginx/Vite doit proxifier `/api`.
* Test : `curl -s http://localhost:8080/healthz`.
* En développement Vite : `VITE_BACKEND_URL` doit pointer vers `http://127.0.0.1:8000`.

---

## Authentification

| Symptôme | Cause / solution |
|---|---|
| 401 immédiat après login | horloge du serveur décalée (> 5 min) ou `SECRET_KEY` changé |
| 403 « Compte désactivé » | `is_active=false` (admin) |
| Boucle de redirection `/login` | jeton corrompu dans `localStorage` : videz le stockage du site |
| Mot de passe admin oublié | voir ci-dessous |

```bash
# réinitialiser le mot de passe admin (backend dans Docker)
docker compose exec backend python - <<'PY'
from sqlalchemy import select
from app.core.passwords import hash_password
from app.db.session import SessionLocal
from app.models.user import User

with SessionLocal() as db:
    user = db.scalars(select(User).where(User.role == 'admin')).first()
    user.password_hash = hash_password('NouveauMotDePasse2026')
    db.commit()
    print('Mot de passe réinitialisé pour', user.email)
PY
```

---

## Imports

### « Playlist invalide : aucune entrée #EXTINF »
Le fichier n'est pas un M3U (HTML d'erreur, JSON, XMLTV). Vérifiez son contenu :
les lignes doivent commencer par `#EXTM3U` puis `#EXTINF:-1 …`.

### « Document trop volumineux »
Au-delà de 40 Mo (`MAX_PLAYLIST_BYTES`). Découpez la playlist ou augmentez la limite.

### « Adresse réseau privée non autorisée »
Protection SSRF : une URL pointant vers `192.168.x.x`, `10.x.x.x`, `127.0.0.1` est refusée.
Pour un flux LAN, mettez `ALLOW_PRIVATE_STREAM_HOSTS=true` (risque assumé) et redémarrez.

### Téléchargement très lent / timeout
`HTTP_TIMEOUT_SECONDS=25` par défaut. Augmentez à 60 pour un fournisseur lent, ou importez le
fichier manuellement.

### Xtream « identifiants refusés »
* URL du portail sans `/player_api.php` (PrimeTV normalise) ;
* vérifiez le port et le schéma (http/https) ;
* compte expiré côté fournisseur.

### Les chaînes importées n'apparaissent pas
`replace=true` supprime les chaînes absentes de la nouvelle version ; vérifiez le récapitulatif
d'import (créées / mises à jour / supprimées) et le filtre « Toutes les chaînes » (les radios
nécessitent le filtre Radios ou l'affichage complet).

---

## Lecture

### Écran noir / « Ce flux ne peut pas être décodé »
* format non supporté par le navigateur (ex. MPEG-TS brut) : la lecture web nécessite HLS/DASH/MP4 ;
* source hors ligne : testez `POST /channels/{id}/refresh` ;
* User-Agent bloqué : le proxy relaie avec le User-Agent PrimeTV ; certains serveurs exigent celui
  d'un lecteur précis (limite connue).

### Erreur CORS
Le proxy doit être utilisé (`play?proxy=true`, valeur par défaut). Si vous appelez l'API depuis un
autre domaine, renseignez `CORS_ORIGINS`.

### 403 sur `/streams/proxy`
L'URL demandée n'appartient pas au domaine du flux (protection anti-relais).
Les CDN utilisant un domaine radicalement différent ne sont pas relayés : utilisez `direct_url`.

### Pas de son / pas d'image
Vérifiez le volume du lecteur et le codec : certains flux HEVC/AC-3 ne sont pas décodés par tous
les navigateurs. L'application est une web app unique — testez un autre navigateur si besoin.

### DRM affiché, lecture impossible
Comportement attendu : PrimeTV ne contourne pas Widevine/PlayReady/FairPlay.
Utilisez une source libre ou un lecteur agréé par le fournisseur.

### Clé ClearKey refusée
Format attendu : 32 caractères hexadécimaux (16 octets). `kid` et `key` identiques en longueur.

### Picture in Picture inactif
Disponible si le navigateur le permet et si la page est en HTTPS (ou localhost). Firefox/Safari
peuvent le désactiver.

---

## EPG

### « Aucun programme EPG »
* source non synchronisée : bouton **Synchroniser** ;
* association manquante : renseignez `tvg-id` dans la playlist ou modifiez la chaîne
  (`PATCH /channels/{id}` avec `tvg_id`) ;
* EPG vide ou expiré côté fournisseur.

### Programme décalé d'une heure
Les dates XMLTV sont converties en UTC. Vérifiez le `tvg-shift` de la playlist (non appliqué
automatiquement) et le fuseau du navigateur.

### Guide très lent
Beaucoup de programmes : purgez les anciens (`DELETE FROM epg_programmes WHERE stop_at < now() - interval '7 days'`)
et limitez la fenêtre (`?hours=12`).

---

## Scan

### Toutes les chaînes passent « hors ligne »
Le serveur n'a pas d'accès Internet, ou les sources bloquent l'IP. Testez :

```bash
docker compose exec backend python -c "import httpx; print(httpx.get('https://example.com', timeout=5).status_code)"
```

### Scan très long
`PROBE_CONCURRENCY=8` : augmentez à 16 sur un serveur confortable, ou scannez playlist par playlist.
`SCAN_MAX_CHANNELS` limite le nombre de chaînes par job.

### Le job reste `queued`
Le worker d'arrière-plan est lié au process : si le conteneur a redémarré pendant le job, relancez-le.
Consultez `GET /scan/jobs/{id}`.

---

## Frontend

### Page blanche après déploiement
Le serveur doit renvoyer `index.html` pour toutes les routes (fallback SPA). Vérifiez la configuration
Nginx (`try_files $uri $uri/ /index.html;`).

### Ancienne version affichée
Assets immuables + `index.html` sans cache : forcez un rechargement (Ctrl+Shift+R) ou vérifiez que
Nginx sert bien le nouveau `dist`.

### Build échoue `Out of memory`
`NODE_OPTIONS=--max-old-space-size=4096 npm run build` ou augmentez la RAM du runner.

---

## Application web / PWA

### Le bouton « Installer » n'apparaît pas
* l'installation exige **HTTPS** (ou `localhost`) et un navigateur compatible
  (Chrome, Edge, Samsung Internet) ;
* le service worker doit être actif : DevTools → Application → Service Workers ;
* sur **iOS**, l'invite n'existe pas : Partager → « Sur l'écran d'accueil ».

### Manifeste introuvable / `404` sur `/sw.js`
Le build n'a pas été refait après l'ajout des fichiers PWA :
`cd web && npm run build`, puis vérifiez que `dist/manifest.webmanifest` et `dist/sw.js` existent.
Avec Nginx, contrôlez le `root` et le `try_files`.

### L'interface reste sur une ancienne version
Le service worker sert l'app shell depuis le cache : `sw.js` est pourtant revalidé à chaque
chargement. Forcez la mise à jour (DevTools → Application → Service Workers → *Update*),
ou fermez tous les onglets PrimeTV puis rouvrez l'application.

### Page blanche après déploiement
Le serveur doit renvoyer `index.html` pour toutes les routes (`try_files $uri $uri/ /index.html;`)
et servir les assets sous `/assets/`. Vérifiez aussi `base` dans `vite.config.ts` (laisser `/`).

### Mode hors ligne sans intérêt / API figée
Comportement normal : `/api/**` n'est jamais mis en cache. Si vous voulez un catalogue
consultable hors connexion, c'est un chantier produit (cache IndexedDB), non activé par défaut.

### Picthre-in-Picture inactif
Disponible si le navigateur le permet, en HTTPS, et si la vidéo est lancée par un geste
utilisateur. Firefox/Safari peuvent le désactiver.

---

## Base de données

### `too many connections`
Réduisez `DB_POOL_SIZE` par worker, ou augmentez `max_connections` PostgreSQL.

### Le catalogue a doublé après réimport
Deux playlists distinctes contenant les mêmes URL créent deux jeux de chaînes (clé = hash URL
**par playlist**). Importez dans la même playlist (synchronisation) pour éviter les doublons.

### Réinitialiser complètement
```bash
docker compose down
docker volume rm primetv_postgres_data primetv_redis_data
docker compose up -d
```
⚠️ Perte totale des données. Sauvegardez avant.

---

## Journaux utiles

```bash
docker compose logs -f backend          # API
docker compose logs -f nginx            # proxy
docker compose logs -f postgres         # base
docker compose exec backend python -c "import app; print(app.__version__)"
curl -s localhost:8080/api/v1/healthz | jq
```

Fournissez toujours le `X-Request-Id` de la réponse en cas de signalement.
