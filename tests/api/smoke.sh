#!/usr/bin/env bash
# =============================================================================
# PrimeTV — smoke test de l'API REST
# -----------------------------------------------------------------------------
# Vérifie qu'une instance démarrée répond correctement sur les parcours
# critiques : santé, OpenAPI, authentification, catalogue, chaînes, EPG,
# favoris, historique, statistiques et descripteur de lecture.
#
# Usage :
#   BASE_URL=http://localhost:8000 ADMIN_EMAIL=admin@primetv.io \
#   ADMIN_PASSWORD='PrimeTV#2026' ./tests/api/smoke.sh
#
# Options :
#   --quiet   n'affiche que les échecs et le bilan
# Codes de sortie : 0 = tout est vert, 1 = au moins une vérification échouée,
#                   2 = l'API est injoignable / configuration invalide.
# =============================================================================
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"
API="${BASE_URL}/api/v1"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@primetv.io}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-PrimeTV#2026}"
TIMEOUT="${TIMEOUT:-20}"
QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
if [[ ! -t 1 ]]; then C_GREEN=""; C_RED=""; C_YELLOW=""; C_DIM=""; C_OFF=""; fi

PASS=0
FAIL=0
BODY=""
CODE=""
TOKEN=""
CHANNEL_ID=""

log()  { (( QUIET )) || printf '%s\n' "$*"; }
pass() { PASS=$((PASS + 1)); log "  ${C_GREEN}✔${C_OFF} $1"; }
fail() { FAIL=$((FAIL + 1)); printf '  %s✘ %s%s\n' "$C_RED" "$1" "$C_OFF"
         [[ -n "${2:-}" ]] && printf '    %s%s%s\n' "$C_DIM" "${2:0:400}" "$C_OFF"; }

# --- helpers ---------------------------------------------------------------
# Extrait une valeur JSON (notation pointée) du corps de la dernière réponse.
# Le corps est passé par variable d'environnement : le stdin reste libre.
json() {
  JSON_PATH="$1" JSON_BODY="$BODY" python3 -c '
import json, os, sys
data = json.loads(os.environ.get("JSON_BODY") or "null")
for key in os.environ.get("JSON_PATH", "").split("."):
    if isinstance(data, list):
        data = data[int(key)] if key.isdigit() and int(key) < len(data) else None
    elif isinstance(data, dict):
        data = data.get(key)
    else:
        data = None
    if data is None:
        sys.exit(1)
print(data if not isinstance(data, (dict, list)) else json.dumps(data))
' 2>/dev/null
}

# request METHOD PATH [DATA] [AUTH]
# Renseigne CODE et BODY ; renvoie 0 si curl a pu joindre le serveur.
request() {
  local method="$1" path="$2" data="${3:-}" auth="${4:-}"
  local args=(-sS -m "$TIMEOUT" -X "$method" -H 'Accept: application/json')
  [[ -n "$auth" ]] && args+=(-H "Authorization: Bearer ${auth}")
  if [[ -n "$data" ]]; then
    args+=(-H 'Content-Type: application/json' --data "$data")
  fi
  local out
  if ! out=$(curl "${args[@]}" -w '\n%{http_code}' "$path" 2>&1); then
    CODE="000"; BODY="$out"; return 1
  fi
  CODE="${out##*$'\n'}"
  BODY="${out%$'\n'*}"
  return 0
}

# expect NAME EXPECTED_CODE METHOD PATH [DATA] [AUTH]
expect() {
  local name="$1" want="$2" method="$3" path="$4" data="${5:-}" auth="${6:-}"
  if ! request "$method" "$path" "$data" "$auth"; then
    fail "$name (API injoignable)" "$BODY"; return 1
  fi
  if [[ ",$want," == *",$CODE,"* ]]; then
    pass "$name ${C_DIM}[$CODE]${C_OFF}"; return 0
  fi
  fail "$name — attendu $want, reçu $CODE" "$BODY"; return 1
}

cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]]; then rm -rf "$TMP_DIR"; fi
}
TMP_DIR="$(mktemp -d)"
trap cleanup EXIT

# --- 0. disponibilité ------------------------------------------------------
log "PrimeTV — smoke test API"
log "${C_DIM}Cible : ${BASE_URL}${C_OFF}"
log ""
log "Sonde de disponibilité"

if ! curl -fsS -m 5 "${BASE_URL}/healthz" >/dev/null 2>&1; then
  printf '%sL’API ne répond pas sur %s/healthz%s\n' "$C_RED" "$BASE_URL" "$C_OFF"
  printf 'Démarrez-la (docker compose up -d backend, ou ./scripts/dev.sh) puis relancez.\n'
  exit 2
fi
pass "GET /healthz"

# --- 1. système ------------------------------------------------------------
log ""
log "Système"
expect "GET /api/v1/healthz"       200 GET "${API}/healthz"
expect "GET /api/v1/readyz"        "200,503" GET "${API}/readyz"
expect "GET /openapi.json"         200 GET "${BASE_URL}/openapi.json"
if [[ "$CODE" == "200" ]]; then
  ROUTES=$(printf '%s' "$BODY" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("paths",{})))' 2>/dev/null || echo 0)
  if [[ "${ROUTES:-0}" -ge 30 ]]; then pass "OpenAPI : ${ROUTES} chemins documentés"; else fail "OpenAPI trop pauvre (${ROUTES} chemins)"; fi
fi
expect "GET /docs (Swagger UI)"    "200,404" GET "${BASE_URL}/docs"

# --- 2. authentification ---------------------------------------------------
log ""
log "Authentification"
expect "POST /auth/login (mauvais mot de passe → 401)" 401 POST "${API}/auth/login" \
  '{"email":"invalide@primetv.io","password":"motdepasse-faux"}'

if ! expect "POST /auth/login (admin)" 200 POST "${API}/auth/login" \
  "$(printf '{"email":"%s","password":"%s"}' "$ADMIN_EMAIL" "$ADMIN_PASSWORD")"; then
  printf '%sIdentifiants de démonstration refusés.%s\n' "$C_YELLOW" "$C_OFF"
  printf 'Renseignez ADMIN_EMAIL / ADMIN_PASSWORD, ou créez un compte via /auth/register.\n'
  printf '\n%sBilan : %d réussite(s), %d échec(s)%s\n' "$C_RED" "$PASS" "$FAIL" "$C_OFF"
  exit 1
fi
TOKEN=$(printf '%s' "$BODY" | json access_token)
if [[ -z "$TOKEN" ]]; then
  printf '%sRéponse de login sans access_token%s\n' "$C_RED" "$C_OFF"
  exit 1
fi
pass "Jeton d'accès reçu (${#TOKEN} caractères)"

expect "GET /auth/me"              200 GET "${API}/auth/me" "" "$TOKEN"
ROLE=$(printf '%s' "$BODY" | json role)
[[ -n "$ROLE" ]] && pass "Rôle du compte : ${ROLE}"
expect "GET /auth/me sans jeton → 401" 401 GET "${API}/auth/me"
expect "GET /profiles"             200 GET "${API}/profiles" "" "$TOKEN"

# --- 3. catalogue ----------------------------------------------------------
log ""
log "Catalogue"
expect "GET /catalog/categories"   200 GET "${API}/catalog/categories" "" "$TOKEN"
expect "GET /catalog/languages"    200 GET "${API}/catalog/languages" "" "$TOKEN"
expect "GET /catalog/bouquets"     200 GET "${API}/catalog/bouquets" "" "$TOKEN"
expect "GET /catalog/facets"       200 GET "${API}/catalog/facets" "" "$TOKEN"

# --- 4. chaînes ------------------------------------------------------------
log ""
log "Chaînes"
if expect "GET /channels (page 1, tri par défaut)" 200 GET "${API}/channels?page=1&page_size=5" "" "$TOKEN"; then
  TOTAL=$(printf '%s' "$BODY" | json total)
  CHANNEL_ID=$(printf '%s' "$BODY" | json items.0.id)
  pass "Catalogue : ${TOTAL:-0} chaîne(s) accessible(s)"
fi
expect "GET /channels?category=sport" 200 GET "${API}/channels?category=sport&page_size=3" "" "$TOKEN"
expect "GET /channels?language=ar"    200 GET "${API}/channels?language=ar&page_size=3" "" "$TOKEN"
expect "GET /channels?radio=true"     200 GET "${API}/channels?radio=true&page_size=3" "" "$TOKEN"
expect "GET /channels?q=tunisie"      200 GET "${API}/channels?q=tunisie&page_size=3" "" "$TOKEN"
expect "GET /channels/{inconnu} → 404" 404 GET "${API}/channels/00000000-0000-0000-0000-000000000000" "" "$TOKEN"
expect "GET /channels/ids"            200 GET "${API}/channels/ids" "" "$TOKEN"
if [[ -n "$CHANNEL_ID" ]]; then
  expect "GET /channels/{id}"         200 GET "${API}/channels/${CHANNEL_ID}" "" "$TOKEN"
  expect "GET /channels/{id}/epg"     "200,404" GET "${API}/channels/${CHANNEL_ID}/epg" "" "$TOKEN"
  if expect "GET /channels/{id}/play" 200 GET "${API}/channels/${CHANNEL_ID}/play" "" "$TOKEN"; then
    PLAY_URL=$(printf '%s' "$BODY" | json url)
    PLAY_TYPE=$(printf '%s' "$BODY" | json stream_type)
    if [[ -n "$PLAY_URL" ]]; then pass "Descripteur de lecture : type=${PLAY_TYPE}"; else fail "Descripteur de lecture sans URL"; fi
  fi
fi

# --- 5. EPG, favoris, historique, réglages --------------------------------
log ""
log "EPG · favoris · historique · réglages"
expect "GET /epg/sources"          200 GET "${API}/epg/sources" "" "$TOKEN"
expect "GET /epg/guide"            "200,422" GET "${API}/epg/guide" "" "$TOKEN"
expect "GET /favorites"            200 GET "${API}/favorites" "" "$TOKEN"
expect "GET /history"              200 GET "${API}/history" "" "$TOKEN"
expect "GET /history/continue"     200 GET "${API}/history/continue" "" "$TOKEN"
expect "GET /history/recent"       200 GET "${API}/history/recent" "" "$TOKEN"
expect "GET /settings"             200 GET "${API}/settings" "" "$TOKEN"
expect "PUT /settings (clé de test)" 200 PUT "${API}/settings" \
  '{"key":"smoke_test","value":{"ok":true}}' "$TOKEN"
expect "DELETE /settings/smoke_test" 200 DELETE "${API}/settings/smoke_test" "" "$TOKEN"

# --- 6. playlists, fournisseurs, statistiques -----------------------------
log ""
log "Playlists · fournisseurs · statistiques · scan"
expect "GET /playlists"            200 GET "${API}/playlists" "" "$TOKEN"
expect "GET /providers"            200 GET "${API}/providers" "" "$TOKEN"
expect "GET /stats/dashboard"      200 GET "${API}/stats/dashboard" "" "$TOKEN"
if [[ "$CODE" == "200" ]]; then
  CH=$(printf '%s' "$BODY" | json channels 2>/dev/null)
  pass "Tableau de bord : $(printf '%s' "$BODY" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(", ".join(f"{k}={d[k]}" for k in ("channels","bouquets","playlists","active_streams") if k in d))' 2>/dev/null)"
fi
expect "GET /stats/activity"       200 GET "${API}/stats/activity?limit=5" "" "$TOKEN"
expect "GET /scan/jobs"            200 GET "${API}/scan/jobs" "" "$TOKEN"
expect "GET /scan/latest"          "200,204,404" GET "${API}/scan/latest" "" "$TOKEN"

# --- 7. validations --------------------------------------------------------
log ""
log "Validation des entrées"
expect "POST /playlists (URL non autorisée → 422)" "400,422" POST "${API}/playlists" \
  '{"name":"smoke","url":"file:///etc/passwd","content_type":"m3u"}' "$TOKEN"
expect "POST /playlists (corps vide → 422)"        "400,422" POST "${API}/playlists" "{}" "$TOKEN"
expect "GET /favorites sans jeton → 401"           401 GET "${API}/favorites"

# --- 8. bilan --------------------------------------------------------------
TOTAL=$((PASS + FAIL))
log ""
if (( FAIL == 0 )); then
  printf '%s✔ Smoke test réussi : %d/%d vérifications%s\n' "$C_GREEN" "$PASS" "$TOTAL" "$C_OFF"
  exit 0
fi
printf '%s✘ Smoke test : %d réussite(s), %d échec(s) sur %d%s\n' "$C_RED" "$PASS" "$FAIL" "$TOTAL" "$C_OFF"
exit 1
