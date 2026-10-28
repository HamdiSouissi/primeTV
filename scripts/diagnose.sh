#!/usr/bin/env bash
# =============================================================================
# PrimeTV — diagnostic du 502 / « l'API ne répond pas »
# -----------------------------------------------------------------------------
# Enchaîne les vérifications dans l'ordre où un 502 se produit :
#   1. état des conteneurs        (backend arrêté / en restart / unhealthy)
#   2. journaux du backend        (erreur d'import, base de données, gunicorn)
#   3. résolution DNS depuis nginx (nom `backend` introuvable)
#   4. connectivité nginx → API   (curl depuis le conteneur nginx)
#   5. API depuis l'hôte          (/healthz, /api/v1/config)
#   6. configuration (.env, mots de passe, ports occupés)
#
# Usage :  ./scripts/diagnose.sh [--no-color]
# Code :   0 = tout est vert, 1 = anomalie détectée, 2 = Docker indisponible
# =============================================================================
set -uo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_OFF=$'\033[0m'
[[ ! -t 1 || "${1:-}" == "--no-color" ]] && { C_RED=""; C_GREEN=""; C_YELLOW=""; C_DIM=""; C_BOLD=""; C_OFF=""; }

PROBLEMS=0
ok()   { printf '  %s✔%s %s\n' "$C_GREEN" "$C_OFF" "$1"; }
bad()  { PROBLEMS=$((PROBLEMS + 1)); printf '  %s✘%s %s\n' "$C_RED" "$C_OFF" "$1"; }
warn() { printf '  %s!%s %s\n' "$C_YELLOW" "$C_OFF" "$1"; }
info() { printf '    %s%s%s\n' "$C_DIM" "$1" "$C_OFF"; }
step() { printf '\n%s== %s%s\n' "$C_BOLD" "$1" "$C_OFF"; }

HTTP_PORT="$(grep -E '^HTTP_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d ' ')"
HTTP_PORT="${HTTP_PORT:-8080}"
BASE="http://localhost:${HTTP_PORT}"

if ! command -v docker >/dev/null 2>&1; then
  printf '%sDocker introuvable%s : ce script vérifie une pile Docker Compose.\n' "$C_RED" "$C_OFF"
  printf 'Pour un lancement local, utilisez ./scripts/dev.sh (API :8000, web :5173).\n'
  exit 2
fi

printf '%sPrimeTV — diagnostic%s (proxy attendu sur %s)\n' "$C_BOLD" "$C_OFF" "$BASE"

# --- 1. conteneurs -----------------------------------------------------------
step "1. Conteneurs"
if ! docker compose ps >/tmp/primetv_ps.txt 2>/dev/null; then
  bad "docker compose ne répond pas (Docker Desktop démarré ? mauvais répertoire ?)"
  cat /tmp/primetv_ps.txt 2>/dev/null | head -5
  exit 2
fi
sed 's/^/    /' /tmp/primetv_ps.txt

get_state() { docker compose ps --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null | awk -v svc="$1" '$1==svc {print $2" "$3}'; }

for svc in postgres redis backend web nginx; do
  state="$(get_state "$svc")"
  if [[ -z "$state" ]]; then
    bad "service « $svc » absent (conteneur non créé) → docker compose up -d --build"
  elif [[ "$state" == running*"healthy"* || "$state" == "running " ]]; then
    ok "$svc : $state"
  elif [[ "$state" == *"unhealthy"* ]]; then
    bad "$svc : $state → voir « docker compose logs --tail=80 $svc »"
  else
    bad "$svc : $state → « docker compose up -d $svc »"
  fi
done

# --- 2. journaux backend -----------------------------------------------------
step "2. Journaux du backend (30 dernières lignes)"
if docker compose logs --tail=30 backend > /tmp/primetv_backend.log 2>&1; then
  if grep -qE 'Traceback|ModuleNotFoundError|OperationalError|CRITICAL|Worker failed|exited' /tmp/primetv_backend.log; then
    bad "des erreurs apparaissent dans les journaux du backend :"
    grep -E 'Traceback|Error|error|CRITICAL|Worker failed|exited' /tmp/primetv_backend.log | tail -8 | sed 's/^/      /'
  else
    ok "aucune erreur évidente dans les journaux"
  fi
  grep -E 'Base de données prête|Booting worker|Listening at|Redis' /tmp/primetv_backend.log | tail -4 | sed 's/^/      /'
else
  warn "conteneur backend introuvable (pas de journaux)"
fi

# --- 3. DNS interne ----------------------------------------------------------
step "3. Résolution du nom « backend » depuis nginx"
if dns="$(docker compose exec -T nginx getent hosts backend 2>/dev/null)"; then
  ok "backend → $(echo "$dns" | awk '{print $1}' | head -1)"
else
  bad "nginx ne résout pas « backend » (conteneurs sur des réseaux différents ?)"
  info "Vérifiez qu'ils partagent bien « primetv_net » : docker compose ps --format '{{.Service}}'"
fi

# --- 4. nginx → API ----------------------------------------------------------
step "4. Nginx → API (depuis le conteneur nginx)"
if code="$(docker compose exec -T nginx curl -fsS -o /dev/null -w '%{http_code}' --max-time 5 http://backend:8000/healthz 2>/dev/null)"; then
  ok "GET http://backend:8000/healthz → $code"
else
  bad "connection refusée/timeout depuis nginx vers backend:8000"
  info "Le backend écoute-t-il bien sur 8000 ? (PORT ne doit pas être défini dans .env)"
fi

# --- 5. API depuis l'hôte ----------------------------------------------------
step "5. API depuis l'hôte"
for path in /nginx-health /healthz /api/v1/config; do
  code="$(curl -s -o /tmp/primetv_body.txt -w '%{http_code}' --max-time 8 "${BASE}${path}" 2>/dev/null)"
  case "$code" in
    200) ok "GET $path → 200" ;;
    502) bad "GET $path → 502 (proxy OK, backend injoignable)"; info "$(head -c 200 /tmp/primetv_body.txt)" ;;
    000) bad "GET $path → aucune réponse (nginx arrêté ou port $HTTP_PORT fermé)" ;;
    *)   warn "GET $path → $code" ;;
  esac
done

# --- 6. configuration --------------------------------------------------------
step "6. Configuration"
if [[ -f .env ]]; then
  ok ".env présent"
  if grep -qE 'change-me|CHANGEME|__REMPLACER__' .env; then
    bad "valeurs d'exemple non remplacées dans .env (SECRET_KEY, mots de passe)"
    info "Relancez ./scripts/install.sh ou éditez .env puis docker compose up -d"
  fi
  if grep -qE '^PORT=' .env; then
    bad "« PORT » est défini dans .env : il est transmis au conteneur backend et peut décaler gunicorn"
    info "Supprimez la ligne PORT= (le port interne doit rester 8000)"
  fi
  if grep -qE '^DATABASE_URL=.*change-me' .env; then
    bad "DATABASE_URL contient encore le mot de passe d'exemple"
  fi
else
  bad ".env absent → cp .env.example .env (ou ./scripts/install.sh)"
fi

for port in "$HTTP_PORT" "${HTTPS_PORT:-8443}"; do
  if command -v ss >/dev/null 2>&1; then
    holder="$(ss -ltnp 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print $6}' | head -1)"
    [[ -n "$holder" ]] && info "port $port écouté par ${holder}"
  fi
done

# --- bilan -------------------------------------------------------------------
printf '\n'
if (( PROBLEMS == 0 )); then
  printf '%s✔ Aucune anomalie détectée.%s\n' "$C_GREEN" "$C_OFF"
  printf 'Si le navigateur affiche encore une erreur : videz le cache (Ctrl+Shift+R) et vérifiez\n'
  printf 'que vous ouvrez bien %s et non une ancienne instance.\n' "$BASE"
  exit 0
fi

printf '%s✘ %d anomalie(s).%s Correctifs les plus fréquents :\n' "$C_RED" "$PROBLEMS" "$C_OFF"
cat <<'EOF'
    1. Backend arrêté / en boucle   → docker compose logs --tail=100 backend
                                      docker compose up -d --force-recreate backend
    2. Backend recréé (IP changée)  → docker compose restart nginx
                                      (corrigé en 1.0.2 : résolution DNS dynamique)
    3. Mot de passe différent       → aligner POSTGRES_PASSWORD et DATABASE_URL dans .env
    4. Base pas encore prête        → attendre 30 s, puis docker compose ps
    5. Tout reconstruire            → docker compose down && docker compose up -d --build
EOF
exit 1
