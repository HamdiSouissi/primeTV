#!/usr/bin/env bash
# =============================================================================
# PrimeTV — installation en une commande (Docker Compose)
#   ./scripts/install.sh              installation standard (HTTP :8080)
#   ./scripts/install.sh --tls        avec Traefik + Let's Encrypt
#   ./scripts/install.sh --demo-off   sans catalogue de démonstration
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"
info()  { printf "${BOLD}→${RESET} %s\n" "$*"; }
ok()    { printf "${GREEN}✓${RESET} %s\n" "$*"; }
warn()  { printf "${YELLOW}!${RESET} %s\n" "$*"; }
fail()  { printf "${RED}✗${RESET} %s\n" "$*" >&2; exit 1; }

PROFILE=""
DEMO="true"
for arg in "$@"; do
  case "$arg" in
    --tls) PROFILE="--profile tls" ;;
    --demo-off) DEMO="false" ;;
    -h|--help)
      grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//' | head -10
      exit 0 ;;
    *) warn "Argument inconnu : $arg" ;;
  esac
done

info "Vérification des prérequis"
command -v docker >/dev/null 2>&1 || fail "Docker n'est pas installé (https://docs.docker.com/engine/install/)"
docker compose version >/dev/null 2>&1 || fail "Le plugin Docker Compose v2 est requis"
docker info >/dev/null 2>&1 || fail "Le démon Docker n'est pas démarré (sudo systemctl start docker)"
ok "Docker et Docker Compose disponibles"

info "Préparation du fichier .env"
if [[ -f .env ]]; then
  ok ".env existant conservé"
else
  cp .env.example .env
  python3 - <<'PY'
import pathlib, secrets
path = pathlib.Path(".env")
content = path.read_text()
secret_key = secrets.token_urlsafe(48)
pg_password = secrets.token_urlsafe(24).replace("-", "x").replace("_", "y")
content = content.replace("SECRET_KEY=change-me-with-openssl-rand-base64-48", f"SECRET_KEY={secret_key}")
content = content.replace("POSTGRES_PASSWORD=change-me-postgres-password", f"POSTGRES_PASSWORD={pg_password}")
content = content.replace(
    "DATABASE_URL=postgresql+psycopg://primetv:change-me-postgres-password@postgres:5432/primetv",
    f"DATABASE_URL=postgresql+psycopg://primetv:{pg_password}@postgres:5432/primetv",
)
path.write_text(content)
PY
  chmod 600 .env
  ok ".env généré avec des secrets aléatoires"
fi

if [[ "$DEMO" == "false" ]]; then
  sed -i 's/^SEED_DEMO_DATA=.*/SEED_DEMO_DATA=false/' .env
  info "Catalogue de démonstration désactivé"
fi

info "Génération du certificat TLS local (si absent)"
./scripts/gen-self-signed-cert.sh "${TRAEFIK_DOMAIN:-localhost}" >/dev/null 2>&1 || warn "openssl indisponible : Nginx générera le certificat au démarrage"

info "Construction et démarrage des conteneurs (quelques minutes la première fois)"
docker compose $PROFILE up -d --build

info "Attente de la disponibilité de l'API…"
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${HTTP_PORT:-8080}/healthz" >/dev/null 2>&1; then break; fi
  sleep 3
done

if curl -fsS "http://localhost:${HTTP_PORT:-8080}/healthz" >/dev/null 2>&1; then
  ok "PrimeTV est en ligne"
else
  warn "L'API ne répond pas encore : consultez « docker compose logs -f backend »"
fi

ADMIN_EMAIL="$(grep -E '^DEFAULT_ADMIN_EMAIL=' .env | cut -d= -f2)"
ADMIN_PASSWORD="$(grep -E '^DEFAULT_ADMIN_PASSWORD=' .env | cut -d= -f2)"

cat <<MSG

${BOLD}PrimeTV est installé.${RESET}

  Interface web   : http://localhost:${HTTP_PORT:-8080}
  Application Flutter (web) : http://localhost:${HTTP_PORT:-8080}/mobile/
  Documentation API : http://localhost:${HTTP_PORT:-8080}/docs
  Traefik (si --tls) : https://${TRAEFIK_DOMAIN:-primetv.localhost}

  Identifiants administrateur initiaux :
    email    : ${ADMIN_EMAIL}
    password : ${ADMIN_PASSWORD}

  ⚠️  Changez ce mot de passe dès la première connexion (Réglages → Sécurité).

  Commandes utiles :
    docker compose logs -f backend
    docker compose ps
    ./scripts/backup.sh          sauvegarde PostgreSQL
    ./scripts/update.sh          mise à jour
    docker compose down          arrêt

MSG
