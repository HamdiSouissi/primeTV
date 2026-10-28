#!/usr/bin/env bash
# =============================================================================
# PrimeTV — environnement de développement local (sans Docker)
#   - API FastAPI  : http://localhost:8000 (rechargement auto)
#   - Web Vite     : http://localhost:5173
#   - SQLite par défaut, Redis facultatif
# =============================================================================
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v python3 >/dev/null || { echo "Python 3.11+ requis"; exit 1; }
command -v npm >/dev/null || { echo "Node 20+ requis"; exit 1; }

if [[ ! -d backend/.venv ]]; then
  echo "→ Création de l'environnement Python"
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install --upgrade pip
  backend/.venv/bin/pip install -r backend/requirements-dev.txt
fi

if [[ ! -d web/node_modules ]]; then
  echo "→ Installation des dépendances frontend"
  (cd web && npm install)
fi

cleanup() {
  echo
  echo "→ Arrêt des services de développement"
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ API : http://localhost:8000/docs"
(
  cd backend
  DATABASE_URL="${DATABASE_URL:-sqlite:///./primetv_local.db}" \
  SEED_DEMO_DATA="${SEED_DEMO_DATA:-true}" \
  PUBLIC_BASE_URL="http://localhost:5173" \
  .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) &

echo "→ Web : http://localhost:5173"
(
  cd web
  VITE_BACKEND_URL="http://127.0.0.1:8000" npm run dev
) &

wait
