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

### Nginx redémarre en boucle (TLS)
Certificat absent et `openssl` indisponible dans l'image : vérifiez
`docker compose logs nginx`, supprimez `docker/nginx/certs/*` et relancez
(`docker compose restart nginx` régénère un certificat auto-signé).

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
Vérifiez le volume du lecteur et le codec (certains flux AAC/HEVC ne sont pas décodés par tous
les navigateurs). Sur Android, ExoPlayer gère davantage de codecs.

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

## Android / Flutter

### `Cleartext HTTP traffic not permitted`
Le manifeste autorise déjà `usesCleartextTraffic="true"`. En production, utilisez HTTPS.

### Écran blanc au lancement
Vérifiez `API_BASE_URL` (`--dart-define`) et la connectivité ; l'app affiche l'URL appelée
sur l'écran de connexion.

### Impossible de se connecter depuis un appareil physique
Utilisez l'IP LAN de la machine (`http://192.168.1.20:8080/api/v1`), pas `localhost`.
Ouvrez le port 8080 dans le pare-feu.

### `flutter pub get` échoue
Vérifiez la version de Flutter (≥ 3.22) et votre accès à pub.dev ; en entreprise, configurez un proxy
`PUB_HOSTED_URL`.

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
