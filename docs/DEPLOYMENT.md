# Déploiement & production

## 1. Dimensionnement

| Usage | vCPU | RAM | Disque |
|---|---|---|---|
| Test / famille (< 10 utilisateurs) | 1–2 | 2 Go | 10 Go |
| Petite instance (10–50) | 2 | 4 Go | 20 Go |
| Instance publique (50–300) | 4 | 8 Go | 50 Go (EPG inclus) |

Le proxy de lecture ne transcode pas : la bande passante est celle des flux, pas du serveur
(mais chaque spectateur consomme la sortie du proxy : surveillez `nginx` et `PROBE_CONCURRENCY`).

## 2. Déploiement recommandé : Docker Compose + Traefik

```bash
git clone https://github.com/HamdiSouissi/primeTV.git /opt/primeTV
cd /opt/primeTV
cp .env.example .env
nano .env    # domaine, secrets, ALLOW_REGISTRATION=false, SEED_DEMO_DATA=false
TRAEFIK_DOMAIN=tv.example.com TRAEFIK_ACME_EMAIL=admin@example.com \
  docker compose --profile tls up -d --build
```

Prérequis DNS : `A tv.example.com → IP du serveur` ; ports **80** et **443** ouverts
(le challenge HTTP-01 de Let's Encrypt utilise le port 80).

Le service `nginx` est **construit depuis `docker/nginx/Dockerfile`** (configuration et script de
certificat embarqués, `openssl` inclus, `nginx -t` exécuté au build) : pensez à
`docker compose build nginx` après toute modification de `docker/nginx/*.conf`. La
configuration est validée au build sur une copie neutralisant les amonts Docker
(`backend:8000`/`web:80` ne sont pas résolubles dans un `docker build`).
Le service `nginx` reste l'entrée interne (Traefik → nginx:80) : sécurité, gzip, limites de débit
et routage `/api`, `/docs`, SPA/PWA restent centralisés.

### Traefik sans `--profile`

Pour utiliser un cluster Traefik existant, supprimez `ports: 80/443` du service `nginx` et exposez-le
sur le réseau Docker avec les labels :

```yaml
labels:
  - traefik.enable=true
  - traefik.docker.network=traefik
  - traefik.http.routers.primetv.rule=Host(`tv.example.com`)
  - traefik.http.routers.primetv.entrypoints=websecure
  - traefik.http.routers.primetv.tls.certresolver=le
  - traefik.http.services.primetv.loadbalancer.server.port=80
```

## 3. Déploiement sans Docker

* Backend : Gunicorn + `uvicorn.workers.UvicornWorker`, `--workers $((2*vCPU))`.
* Frontend : `npm ci && npm run build` → `web/dist` servi par Nginx (voir `web/nginx.conf`).
* Nginx d'entrée : reprenez `docker/nginx/nginx.conf` en remplaçant les `upstream` par
  `127.0.0.1:8000` (API) et le chemin de `dist`.
* systemd : unités `primetv-api` + `nginx` (exemple dans [INSTALL.md](INSTALL.md#34-systemd-exemple-backend)).

## 4. Application web (PWA) en production

Le front-end est un **unique** conteneur Nginx (`web/`) qui sert le build Vite :

```bash
docker compose build web && docker compose up -d web
# ou sans Docker :
cd web && npm ci && npm run build        # → web/dist servi par votre Nginx
```

Points à vérifier :

| Élément | Attendu |
|---|---|
| `GET /manifest.webmanifest` | `Content-Type: application/manifest+json` |
| `GET /sw.js` | `Cache-Control: no-cache` + `Service-Worker-Allowed: /` |
| `/assets/*` | `Cache-Control: public, immutable` (fichiers hachés) |
| `index.html` | `no-cache, must-revalidate` |
| Fallback SPA | `try_files $uri $uri/ /index.html` (sinon 404 au rechargement d'une route) |
| **HTTPS** | obligatoire pour l'installation et le service worker |

Le service worker ne met jamais en cache `/api/**` ni les flux vidéo : rien à purger
côté CDN, mais **n'exposez pas** les réponses API à un cache partagé.

Après un déploiement, les clients reçoivent la nouvelle version au prochain chargement
(le `sw.js` est revalidé systématiquement). En cas de doute :

```bash
curl -sI https://tv.example.com/sw.js | grep -i cache-control
```

Procédure détaillée, stratégies de cache et limites : **[PWA.md](PWA.md)**.

## 5. Haute disponibilité & montée en charge

* **Stateless** : l'API ne stocke rien en local → plusieurs répliques derrière un load balancer.
* **Sessions JWT** : pas d'affinité de session nécessaire.
* **Redis** : partagé entre répliques (cache + rate limit cohérents).
* **PostgreSQL** : réplique en lecture si les statistiques deviennent coûteuses.
* **Scans** : un job est exécuté dans le process qui l'a reçu ; pour plusieurs répliques, dédiez un
  service `worker` (entrypoint `RUN_MODE=worker`) et externalisez la file si besoin.
* **Proxy** : évitez de multiplier les répliques qui relaient le même flux ; préférez un cache CDN
  ou un nginx dédié aux segments.

Exemple `docker-compose.scale.yml` :

```yaml
services:
  backend:
    deploy:
      replicas: 3
```

## 6. Reverse proxy externe (Caddy)

```caddyfile
tv.example.com {
    encode gzip
    handle /api/* {
        reverse_proxy 127.0.0.1:8080
    }
    handle /docs* {
        reverse_proxy 127.0.0.1:8080
    }
    handle /sw.js {
        header Cache-Control "no-cache"
        reverse_proxy 127.0.0.1:8080
    }
    handle {
        reverse_proxy 127.0.0.1:8080
    }
}
```

Configurez `CORS_ORIGINS=https://tv.example.com`, `TRUSTED_HOSTS=tv.example.com`.

## 7. Checklist de production

**Sécurité**
- [ ] HTTPS actif, HSTS, redirection 80→443
- [ ] `SECRET_KEY` unique, `.env` en 600, non versionné
- [ ] mot de passe admin changé, inscriptions fermées si privé
- [ ] PostgreSQL et Redis non exposés
- [ ] `DOCS_ENABLED` réévalué selon l'audience
- [ ] sauvegardes chiffrées/testées

**Performance**
- [ ] Redis actif (`/api/v1/healthz` → `"cache":"redis"`)
- [ ] `WEB_CONCURRENCY` adapté au CPU
- [ ] Gzip/HTTP2 vérifiés (`curl -I --http2`)
- [ ] purge EPG planifiée

**Exploitation**
- [ ] healthchecks Docker verts
- [ ] monitoring `/healthz` externe
- [ ] rotation des logs
- [ ] procédure de rollback documentée
- [ ] scan planifié (cron API) :

```cron
0 4 * * * curl -s -X POST http://127.0.0.1:8080/api/v1/scan \
  -H "Authorization: Bearer $PRIMETV_TOKEN" -H 'Content-Type: application/json' \
  -d '{"probe":true}' >/dev/null
```

## 8. Observabilité

* Logs JSON : `LOG_JSON=true` → Loki/ELK ; corrélez avec `X-Request-Id`.
* Métriques système : `docker stats`, cAdvisor, node_exporter.
* Santé applicative : `/healthz` (base + version), `/api/v1/healthz` (cache + uptime).
* Alertes conseillées : API > 5 % de 5xx sur 5 min, taux de chaînes hors ligne > 40 %,
  disque > 80 %, sauvegarde manquante > 36 h.

## 9. Rollback

```bash
cd /opt/primeTV
git log --oneline -5
git checkout <commit_stable>
docker compose up -d --build
# si le schéma a changé :
./scripts/restore.sh backups/primetv-<date>.sql.gz
```

## 10. Mise hors service

```bash
./scripts/backup.sh            # conservez une copie hors serveur
docker compose down
docker compose down -v         # supprime les volumes
```
