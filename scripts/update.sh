#!/usr/bin/env bash
# =============================================================================
# PrimeTV — mise à jour (git pull + reconstruction + redémarrage)
# Une sauvegarde est créée avant toute mise à jour.
# =============================================================================
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

info() { printf "\033[1m→\033[0m %s\n" "$*"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }

info "Sauvegarde préalable de la base de données"
./scripts/backup.sh || printf "\033[33m!\033[0m Sauvegarde impossible (base non démarrée ?) — poursuite\n"

if [[ -d .git ]]; then
  info "Récupération des dernières sources"
  git fetch --all --prune
  git pull --ff-only
  ok "Sources à jour ($(git rev-parse --short HEAD))"
fi

info "Reconstruction des images"
docker compose build --pull

info "Redémarrage des services"
docker compose up -d --remove-orphans

info "Nettoyage des anciennes images"
docker image prune -f >/dev/null

info "Attente de l'API"
for _ in $(seq 1 40); do
  if curl -fsS "http://localhost:${HTTP_PORT:-8080}/healthz" >/dev/null 2>&1; then
    ok "Mise à jour terminée : API disponible"
    exit 0
  fi
  sleep 3
done
printf "\033[33m!\033[0m L'API ne répond pas : docker compose logs -f backend\n"
exit 1
