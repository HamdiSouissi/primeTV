#!/usr/bin/env bash
# =============================================================================
# PrimeTV — suite de tests complète (backend + frontend + smoke API)
# =============================================================================
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

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

echo "== API : smoke test (si l'API est démarrée) =="
if curl -fsS "${BASE_URL:-http://localhost:8000}/healthz" >/dev/null 2>&1; then
  ./tests/api/smoke.sh
else
  echo "API non démarrée : smoke test ignoré"
fi

echo "✓ Toutes les vérifications sont passées."
