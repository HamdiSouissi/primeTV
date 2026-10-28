#!/usr/bin/env bash
# =============================================================================
# PrimeTV — suite de tests complète (backend + frontend + smoke API)
# =============================================================================
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Hygiène : fins de ligne LF =="
./scripts/fix-line-endings.sh --check

echo "== Shell : syntaxe =="
for script in scripts/*.sh tests/api/smoke.sh docker/nginx/10-generate-cert.sh backend/docker-entrypoint.sh; do
  sh -n "$script" 2>/dev/null || bash -n "$script"
  echo "  ✓ $script"
done

echo "== Backend : lint =="
(cd backend && .venv/bin/ruff check app tests)

echo "== Backend : tests =="
(cd backend && .venv/bin/python -m pytest --cov=app --cov-report=term-missing -q)

echo "== Frontend : typecheck =="
(cd web && npm run lint)

echo "== Frontend : tests =="
(cd web && npm run test)

echo "== Frontend : build =="
(cd web && npm run build)

echo "== PWA : artefacts installables =="
for artefact in manifest.webmanifest sw.js offline.html icons/icon-192.png icons/icon-512.png; do
  if [[ -f "web/dist/$artefact" ]]; then
    echo "  ✓ $artefact"
  else
    echo "  ✘ $artefact manquant (build incomplet)" >&2
    exit 1
  fi
done

echo "== API : smoke test (si l'API est démarrée) =="
if curl -fsS "${BASE_URL:-http://localhost:8000}/healthz" >/dev/null 2>&1; then
  ./tests/api/smoke.sh
else
  echo "API non démarrée : smoke test ignoré"
fi

echo "✓ Toutes les vérifications sont passées."
