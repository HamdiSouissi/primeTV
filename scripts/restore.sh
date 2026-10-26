#!/usr/bin/env bash
# =============================================================================
# PrimeTV — restauration d'une sauvegarde PostgreSQL
#   ./scripts/restore.sh backups/primetv-20260101T120000Z.sql.gz
#   ./scripts/restore.sh --latest
# =============================================================================
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
FILE="${1:-}"

if [[ "$FILE" == "--latest" || -z "$FILE" ]]; then
  FILE="$(ls -1t "$BACKUP_DIR"/primetv-*.sql.gz 2>/dev/null | head -1 || true)"
  [[ -z "$FILE" ]] && { printf "\033[31m✗\033[0m Aucune sauvegarde trouvée dans %s\n" "$BACKUP_DIR" >&2; exit 1; }
  printf "\033[1m→\033[0m Dernière sauvegarde : %s\n" "$FILE"
fi

[[ -f "$FILE" ]] || { printf "\033[31m✗\033[0m Fichier introuvable : %s\n" "$FILE" >&2; exit 1; }

if [[ -f .env ]]; then
  set -a; . ./.env; set +a
fi
DB_USER="${POSTGRES_USER:-primetv}"
DB_NAME="${POSTGRES_DB:-primetv}"

printf "\033[33m!\033[0m Cette opération ÉCRASE la base « %s ».\033[0m\n" "$DB_NAME"
read -r -p "Confirmer la restauration ? [oui/NON] " answer
[[ "$answer" == "oui" || "$answer" == "o" ]] || { echo "Annulé."; exit 1; }

printf "\033[1m→\033[0m Arrêt temporaire de l'API\n"
docker compose stop backend

printf "\033[1m→\033[0m Suppression des sessions actives\n"
docker compose exec -T postgres psql -U "$DB_USER" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" >/dev/null

printf "\033[1m→\033[0m Restauration\n"
gunzip -c "$FILE" | docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" >/dev/null

printf "\033[1m→\033[0m Redémarrage de l'API\n"
docker compose start backend

for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:${HTTP_PORT:-8080}/healthz" >/dev/null 2>&1; then
    printf "\033[32m✓\033[0m Restauration terminée, API disponible\n"
    exit 0
  fi
  sleep 2
done
printf "\033[33m!\033[0m API non disponible : docker compose logs backend\n"
