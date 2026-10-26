# Guide administrateur

## 1. Rôles et comptes

* **admin** : accès total (gestion des utilisateurs via `/api/v1/admin/*`).
* **user** : catalogue, imports, favoris, profils.

Le premier compte est créé au démarrage si la table `users` est vide
(`DEFAULT_ADMIN_EMAIL` / `DEFAULT_ADMIN_PASSWORD`).

Actions immédiates après installation :

1. changer le mot de passe administrateur (Réglages → Sécurité) ;
2. mettre `ALLOW_REGISTRATION=false` si l'instance est privée ;
3. vérifier que `SECRET_KEY` n'est pas la valeur de développement ;
4. désactiver `SEED_DEMO_DATA` en production.

### Créer un administrateur supplémentaire

```bash
curl -X POST localhost:8080/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@example.com","username":"ops","password":"MotDePasse2026"}'

# puis, avec un compte admin existant :
curl -X PATCH localhost:8080/api/v1/admin/users/<id> \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' -d '{"role":"admin"}'
```

## 2. Supervision

```bash
docker compose ps                 # état + healthchecks
./scripts/healthcheck.sh          # API, docs, web, manifeste PWA, conteneurs
docker compose logs -f backend    # logs applicatifs (JSON en production)
docker stats                      # CPU / mémoire
```

Endpoints de supervision :

| Endpoint | Usage |
|---|---|
| `GET /healthz` (Nginx & API) | Load balancer / Docker healthcheck |
| `GET /api/v1/healthz` | Statut détaillé : base, cache, uptime |
| `GET /api/v1/stats/dashboard` | Vue métier (compteurs, dernier scan) |
| `GET /api/v1/stats/activity` | Journal d'activité |

Exemple de sonde Uptime Kuma / Prometheus blackbox : `http://<hôte>:8080/healthz` (200 = OK).

## 3. Sauvegardes

```bash
./scripts/backup.sh                      # -> backups/primetv-<UTC>.sql.gz
KEEP_DAYS=30 ./scripts/backup.sh         # rétention personnalisée
BACKUP_DIR=/mnt/nas/primetv ./scripts/backup.sh
```

Planification (cron quotidien 03:15) :

```cron
15 3 * * * cd /opt/primeTV && ./scripts/backup.sh >> /var/log/primetv-backup.log 2>&1
```

Restauration :

```bash
./scripts/restore.sh --latest
./scripts/restore.sh backups/primetv-20260101T031500Z.sql.gz
```

La restauration arrête l'API, écrase la base puis redémarre. **Testez-la au moins une fois par trimestre.**

Ce qui n'est pas sauvegardé (et n'a pas besoin de l'être) : cache Redis, certificats régénérés
automatiquement, images Docker.

## 4. Mises à jour

```bash
./scripts/update.sh
```

Séquence : sauvegarde → `git pull --ff-only` → `docker compose build --pull` → `up -d` →
nettoyage des images → attente de `/healthz`.

En cas d'échec : `docker compose logs backend`, puis retour arrière possible :

```bash
git log --oneline -5
git checkout <commit_précédent>
docker compose up -d --build
./scripts/restore.sh --latest   # uniquement si le schéma a changé
```

## 5. Gestion des utilisateurs

* Liste : `GET /api/v1/admin/users`.
* Promouvoir / désactiver : `PATCH /api/v1/admin/users/{id}` `{"role":"admin"}` ou `{"is_active":false}`.
* Un utilisateur désactivé reçoit 403 sur toutes les routes authentifiées.
* Suppression : à faire directement en base (cascade sur profils, favoris, historique, imports) :

```bash
docker compose exec postgres psql -U primetv -d primetv -c "SELECT id,email,username,role FROM users;"
docker compose exec postgres psql -U primetv -d primetv -c "DELETE FROM users WHERE email='ancien@example.com';"
```

## 6. Imports et catalogue

L'administrateur peut importer des playlists pour son compte puis les partager ? Non :
**chaque compte gère ses propres fournisseurs/playlists**. Le catalogue (chaînes) est commun à
l'instance ; favoris et historique sont par profil.

Recommandations pour un catalogue sain :

* préférer des sources officielles / libres (FAI, chaînes publiques, FAST) ;
* lancer un scan après chaque import pour connaître les flux réellement actifs ;
* surveiller le taux de chaînes `offline` (> 30 % = source obsolète) ;
* éviter les playlists > 20 000 entrées sans nécessité (temps de scan).

Limites configurables : `MAX_IMPORT_CHANNELS`, `SCAN_MAX_CHANNELS`, `PROBE_CONCURRENCY`,
`HTTP_TIMEOUT_SECONDS`.

## 7. Sécurité opérationnelle

| Mesure | Mise en œuvre |
|---|---|
| HTTPS | Traefik (`--tls`) ou certificat Nginx |
| Secrets | `.env` en `chmod 600`, jamais versionné |
| Reverse proxy | Nginx : `server_tokens off`, limites de débit, `client_max_body_size 64m` |
| Pare-feu | n'exposez que 80/443 (ou 8080) ; PostgreSQL/Redis restent sur le réseau interne |
| Rate limiting | `RATE_LIMIT_REQUESTS`, zone Nginx `login_limit` |
| JWT | durée d'accès 12 h, refresh 14 j, rotation possible via `SECRET_KEY` |
| Chiffrement | identifiants fournisseurs chiffrés (Fernet, clé dérivée de `SECRET_KEY`) |
| Logs | JSON (`LOG_JSON=true`), rotation Docker 10 Mo × 5 |
| Mises à jour | images `--pull`, `docker compose build --pull` |

Détails et politique de divulgation : [SECURITY.md](SECURITY.md).

## 8. Performances

* **Redis** : indispensable au-delà de ~20 utilisateurs simultanés (cache + rate limit).
* **Pool SQL** : `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20` par worker.
* **Workers** : `WEB_CONCURRENCY=4` (règle : 2 × vCPU, plafonné à 8).
* **Scan** : `PROBE_CONCURRENCY=8` ; réduisez à 4 sur un serveur avec peu de bande passante.
* **Compression** : Gzip activé (Nginx + middleware API).
* **Cache HTTP** : les assets Vite sont immuables (1 an), l'API renvoie `no-store` sur les manifestes
  (indispensable pour le live).
* **PostgreSQL** : index sur `priority/name`, `category/language/is_radio`, `stream_url` (hash),
  `epg_channel_id`, `start_at/stop_at`. Pour de gros volumes EPG, purgez les programmes passés :

```sql
DELETE FROM epg_programmes WHERE stop_at < now() - interval '7 days';
```

## 9. Journal des erreurs 5xx

Chaque réponse porte un `X-Request-Id`. Retrouvez la trace :

```bash
docker compose logs backend --since 30m | grep '<request-id>'
```

Erreurs fréquentes :

| Code | Cause probable |
|---|---|
| 500 `database_error` | PostgreSQL indisponible / pool épuisé |
| 502 sur `/streams/proxy` | source distante hors ligne ou lente |
| 403 sur `/streams/proxy` | hôte différent du domaine du flux (protection) |
| 429 | limite de débit atteinte |

## 10. Checklist de mise en production

- [ ] `ENV=production`, `DEBUG=false`, `LOG_JSON=true`
- [ ] `SECRET_KEY` et `POSTGRES_PASSWORD` uniques
- [ ] mot de passe admin changé, `ALLOW_REGISTRATION` selon le besoin
- [ ] `SEED_DEMO_DATA=false`
- [ ] `CORS_ORIGINS` et `TRUSTED_HOSTS` limités au domaine
- [ ] HTTPS actif et redirection HTTP→HTTPS
- [ ] sauvegardes planifiées + restauration testée
- [ ] monitoring sur `/healthz`
- [ ] `DOCS_ENABLED` selon l'exposition souhaitée
- [ ] redis et postgres **non** exposés publiquement
