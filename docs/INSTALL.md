# Installation

Trois méthodes : **Docker Compose** (recommandé), **manuel** (Python + Node) ou **développement local**.
L'application Android/Flutter est détaillée en fin de document.

---

## 1. Prérequis

| Composant | Version minimale | Notes |
|---|---|---|
| Docker Engine | 24.x | + plugin `docker compose` v2 |
| Docker Compose | 2.20 | Fourni avec Docker Desktop |
| RAM | 2 Go | 4 Go confortable (build Flutter Web) |
| Disque | 5 Go | Images + volumes |
| Python | 3.11 | Méthode manuelle / développement |
| Node.js | 20 (22 conseillé) | Build frontend |
| Flutter | 3.22 | Application Android / Web |
| OpenSSL | 1.1 | Certificat TLS local |

Ports par défaut : **8080** (HTTP), **8443** (HTTPS), **80/443** si profil Traefik.

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

Attendu : conteneurs `postgres`, `redis`, `backend`, `web`, `mobile-web`, `nginx` en `healthy`.

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

## 5. Application Android

### 5.1 Depuis les sources

```bash
cd mobile
flutter pub get
# Émulateur Android (10.0.2.2 = hôte)
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
# Appareil physique (remplacez par l'IP LAN du serveur)
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8080/api/v1
```

### 5.2 APK de production

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://tv.example.com/api/v1
# ou App Bundle pour le Play Store
flutter build appbundle --release --dart-define=API_BASE_URL=https://tv.example.com/api/v1
```

Le fichier est généré dans `mobile/build/app/outputs/flutter-apk/app-release.apk`.
Pour signer avec votre keystore, voir [DEPLOYMENT.md](DEPLOYMENT.md#4-signature-android).

> Si le dossier `android/` est incomplet après un clone (wrapper Gradle absent), exécutez une fois :
> `cd mobile && flutter create --platforms=android .` puis `flutter pub get`.

### 5.3 Version Web

```bash
cd mobile
flutter build web --release --base-href /mobile/ \
  --dart-define=API_BASE_URL=/api/v1
```

Ou via Docker : `docker compose build mobile-web` (page servie sur `/mobile/`).

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
