#!/usr/bin/env sh
# =============================================================================
# Point d'entrée du conteneur API : attente de PostgreSQL puis lancement.
#   WEB_CONCURRENCY  : nombre de workers gunicorn (défaut : 4)
#   PORT             : port d'écoute (défaut : 8000)
#   RUN_MODE         : "web" (API) | "worker" (tâches) | "shell"
#
# Note : `--keep-alive 75` doit rester SUPÉRIEUR au délai d'inactivité de Nginx,
# sinon Nginx peut réutiliser une connexion que Gunicorn vient de fermer, ce qui
# provoque des « 502 Bad Gateway » intermittents.
# =============================================================================
set -eu

PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-4}"

wait_for_database() {
  python - <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "sqlite:///./primetv_local.db")
deadline = time.time() + int(os.environ.get("DB_WAIT_SECONDS", "60"))
last_error = None
while time.time() < deadline:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Base de données prête", flush=True)
        sys.exit(0)
    except Exception as exc:  # pragma: no cover - dépend de l'infra
        last_error = exc
        time.sleep(2)
print(f"Base de données indisponible : {last_error}", flush=True)
sys.exit(1)
PY
}

wait_for_redis() {
  if [ -z "${REDIS_URL:-}" ]; then return 0; fi
  python - <<'PY'
import os, sys, time
try:
    import redis
except ImportError:
    sys.exit(0)
url = os.environ.get("REDIS_URL", "")
deadline = time.time() + 30
while time.time() < deadline:
    try:
        redis.Redis.from_url(url, socket_connect_timeout=1).ping()
        print("Redis prêt", flush=True)
        sys.exit(0)
    except Exception:
        time.sleep(1)
print("Redis indisponible : le cache mémoire sera utilisé", flush=True)
PY
}

case "${1:-web}" in
  web)
    wait_for_database
    wait_for_redis
    exec gunicorn app.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers "${WORKERS}" \
      --bind "0.0.0.0:${PORT}" \
      --timeout 120 \
      --graceful-timeout 30 \
      --keep-alive 75 \
      --access-logfile - \
      --error-logfile -
    ;;
  worker)
    wait_for_database
    exec python -m app.worker
    ;;
  shell)
    exec /bin/sh
    ;;
  *)
    exec "$@"
    ;;
esac
