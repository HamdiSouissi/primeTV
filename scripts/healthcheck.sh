#!/usr/bin/env bash
# =============================================================================
# PrimeTV — vérification de santé complète (API, base, cache, frontend)
# =============================================================================
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:${HTTP_PORT:-8080}}"
failed=0

check() {
  local label="$1" url="$2"
  if curl -fsS --max-time 8 "$url" >/dev/null 2>&1; then
    printf "\033[32m✓\033[0m %-22s %s\n" "$label" "$url"
  else
    printf "\033[31m✗\033[0m %-22s %s\n" "$label" "$url"
    failed=1
  fi
}

echo "== PrimeTV healthcheck ($BASE_URL) =="
check "API (healthz)" "$BASE_URL/healthz"
check "API détaillée" "$BASE_URL/api/v1/healthz"
check "Documentation" "$BASE_URL/docs"
check "Interface web" "$BASE_URL/"
check "App Flutter Web" "$BASE_URL/mobile/"

echo "== Conteneurs =="
docker compose ps || true

if [[ "$failed" -eq 0 ]]; then
  printf "\033[32mTous les services répondent.\033[0m\n"
else
  printf "\033[31mAu moins un service ne répond pas.\033[0m\n"
  exit 1
fi
