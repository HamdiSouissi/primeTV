# Installation

Trois méthodes : **Docker Compose** (recommandé), **manuel** (Python + Node) ou **développement local**.
PrimeTV est une **application web unique** (installable en PWA) : aucun SDK mobile n'est requis.

---

## 1. Prérequis

| Composant | Version minimale | Notes |
|---|---|---|
| Docker Engine | 24.x | + plugin `docker compose` v2 |
| Docker Compose | 2.20 | Fourni avec Docker Desktop |
| RAM | 2 Go | 4 Go confortable (build du front-end) |
| Disque | 5 Go | Images + volumes |
| Python | 3.11 | Méthode manuelle / développement |
| Node.js | 20 (22 conseillé) | Build du front-end React |
| OpenSSL | 1.1 | Certificat TLS local |

Ports par défaut : **8080** (HTTP), **8443** (HTTPS), **80/443** si profil Traefik.

> **Windows** : clonez avec `git config --global core.autocrlf input` (ou lancez
> `./scripts/fix-line-endings.sh` après le clone). Sans cela, les scripts des conteneurs
> arrivent en CRLF et Docker échoue avec
> `10-primetv-cert.sh: not found` (nginx) ou `env: use -[v]S to pass options in shebang lines`
> (backend). Voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 2. Installation Docker (Linux, macOS, Windows + WSL2)

### 2.1 Linux (Debian/Ubuntu)

```bash
# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER" && newgrp docker

# Utilitaires
sudo apt update && sudo apt install -y git curl openssl jq python3

git clone https://github.com/HamdiSouissi/primeTV.git
cd primeTV
./scripts/install.sh
```

### 2.2 Windows 10/11

1. Installez **Docker Desktop** (backend WSL2) : <https://docs.docker.com/desktop/install/windows-install/>.
2. Installez **Git for Windows** (inclut Git Bash) : <https://git-scm.com/download/win>.
3. Ouvrez **Git Bash** puis :

```bash
git clone https://github.com/HamdiSouissi/primeTV.git
cd primeTV
./scripts/install.sh
```

> Sous PowerShell sans Git Bash, exécutez plutôt :
> ```powershell
> docker compose up -d --build
> ```
> puis créez `.env` en copiant `.env.example` et en remplaçant `SECRET_KEY` et `POSTGRES_PASSWORD`.

### 2.3 macOS

```bash
brew install --cask docker   # ou Docker Desktop
git clone https://github.com/HamdiSouissi/primeTV.git
cd primeTV && ./scripts/install.sh
```

### 2.4 Ce que fait `install.sh`

1. Vérifie Docker + Compose + démon actif ;
2. Crée `.env` avec `SECRET_KEY` et `POSTGRES_PASSWORD` **aléatoires** ;
3. Génère un certificat TLS auto-signé (si `openssl` présent) ;
4. `docker compose up -d --build` ;
5. Attend `/healthz` puis affiche les URLs et le compte administrateur.

Options :

```bash
./scripts/install.sh --tls        # Traefik + Let's Encrypt (domaine requis)
./scripts/install.sh --demo-off   # aucun catalogue de démonstration
```

### 2.5 Vérification

```bash
docker compose ps
./scripts/healthcheck.sh
curl -s localhost:8080/healthz | jq
```

Attendu : conteneurs `postgres`, `redis`, `backend`, `web`, `nginx` en `healthy`.

```bash
curl -s localhost:8080/nginx-health   # ok        (proxy seul)
curl -s localhost:8080/healthz        # {"status":"ok",...} (pile complète)
```

---

## 3. Installation manuelle (sans Docker)

### 3.1 PostgreSQL et Redis

```bash
# Debian/Ubuntu
sudo apt install -y postgresql redis-server python3-venv nodejs npm
sudo -u postgres psql <<'SQL'
CREATE USER primetv WITH PASSWORD 'motdepasse_fort';
CREATE DATABASE primetv OWNER primetv;
\c primetv
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
SQL
```

### 3.2 Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://primetv:motdepasse_fort@localhost:5432/primetv"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="$(openssl rand -base64 48)"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3.3 Frontend

```bash
cd web
npm ci
npm run build            # -> web/dist
npx serve -s dist -l 5173
# ou en développement : npm run dev
```

Servez `web/dist` derrière Nginx en proxyfiant `/api` vers `http://127.0.0.1:8000`.

### 3.4 systemd (exemple backend)

```ini
# /etc/systemd/system/primetv-api.service
[Unit]
Description=PrimeTV API
After=network.target postgresql.service redis-server.service

[Service]
User=primetv
WorkingDirectory=/opt/primetv/backend
EnvironmentFile=/opt/primetv/.env
ExecStart=/opt/primetv/backend/.venv/bin/gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now primetv-api
```

---

## 4. HTTPS

| Méthode | Usage |
|---|---|
| **Traefik** (`--tls`) | Production, domaine public, Let's Encrypt automatique |
| **Certificat auto-signé** | Réseau privé, tests (généré automatiquement par Nginx) |
| **Reverse proxy externe** | Caddy, Nginx, HAProxy déjà en place : pointez vers `http://localhost:8080` |

Avec Traefik, éditez `.env` :

```env
TRAEFIK_DOMAIN=tv.example.com
TRAEFIK_ACME_EMAIL=vous@example.com
FORCE_HTTPS=true
CORS_ORIGINS=https://tv.example.com
TRUSTED_HOSTS=tv.example.com
```

Puis `docker compose --profile tls up -d`. Les ports 80/443 doivent être libres et le DNS pointer
vers le serveur.

---

## 5. Application web installable (PWA)

L'interface est servie en même origine que l'API : aucune configuration supplémentaire.

| Usage | URL |
|---|---|
| Interface | `http://localhost:8080` (production) ou `http://localhost:5173` (développement) |
| Installation | bouton **Installer** dans la barre supérieure, ou menu du navigateur |
| Mode hors ligne | page dédiée `offline.html` servie par le service worker |

### 5.1 Installation sur les appareils

* **Android** (Chrome/Edge/Samsung Internet) : ouvrir l'URL → **Installer l'application**.
* **iOS/iPadOS** (Safari) : Partager → **Sur l'écran d'accueil**.
* **Windows/macOS/Linux** (Chrome/Edge) : icône d'installation de la barre d'adresse.

L'installation exige **HTTPS** (ou `localhost`). Détails, stratégies de cache et limites :
[PWA.md](PWA.md).

### 5.2 Vérifier le service worker et le manifeste

```bash
curl -s http://localhost:8080/manifest.webmanifest | jq '{name, display, icons: (.icons|length)}'
curl -sI http://localhost:8080/sw.js | grep -i 'cache-control'
```

Dans Chrome : **DevTools → Application → Manifest / Service Workers**.

### 5.3 Régénérer les icônes

```bash
cd web && python3 scripts/generate-icons.py
```

---

## 6. Désinstallation

```bash
docker compose down            # arrête les conteneurs
docker compose down -v         # supprime AUSSI les volumes (données perdues !)
```

Sauvegardez avant : `./scripts/backup.sh`.

---

## 7. Dépannage rapide

| Symptôme | Piste |
|---|---|
| `port is already allocated` | Modifiez `HTTP_PORT` / `HTTPS_PORT` dans `.env` |
| Backend en `unhealthy` | `docker compose logs backend` ; vérifiez `DATABASE_URL` |
| `POSTGRES_PASSWORD est requis` | `.env` absent : `cp .env.example .env` puis éditez |
| Interface vide / erreurs 404 API | Nginx doit proxifier `/api` ; vérifiez `docker compose ps` |
| Certificat refusé par le navigateur | Normal en auto-signé ; utilisez Traefik en production |

Voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md) pour la liste complète.
