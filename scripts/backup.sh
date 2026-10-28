#!/usr/bin/env bash
# =============================================================================
# PrimeTV — sauvegarde PostgreSQL (dump compressé + rotation)
#   BACKUP_DIR  : dossier de destination (défaut ./backups)
#   KEEP_DAYS   : rétention en jours (défaut 14)
# =============================================================================
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="$BACKUP_DIR/primetv-$STAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

# Charge les variables (POSTGRES_USER / POSTGRES_DB)
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
DB_USER="${POSTGRES_USER:-primetv}"
DB_NAME="${POSTGRES_DB:-primetv}"

printf "\033[1m→\033[0m Sauvegarde de la base « %s »…\n" "$DB_NAME"
if ! docker compose ps postgres --status running >/dev/null 2>&1; then
  printf "\033[31m✗\033[0m Le conteneur PostgreSQL n'est pas démarré\n" >&2
  exit 1
fi

docker compose exec -T postgres pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner \
  | gzip -9 > "$FILE"

if [[ ! -s "$FILE" ]]; then
  printf "\033[31m✗\033[0m Dump vide : sauvegarde annulée\n" >&2
  rm -f "$FILE"
  exit 1
fi

chmod 600 "$FILE"
printf "\033[32m✓\033[0m Sauvegarde créée : %s (%s)\n" "$FILE" "$(du -h "$FILE" | cut -f1)"

# Rotation
find "$BACKUP_DIR" -name 'primetv-*.sql.gz' -type f -mtime "+$KEEP_DAYS" -print -delete | while read -r old; do
  printf "  · supprimé : %s\n" "$old"
done

printf "\033[1m→\033[0m Sauvegardes disponibles :\n"
ls -lh "$BACKUP_DIR"/primetv-*.sql.gz 2>/dev/null | tail -5 || true
