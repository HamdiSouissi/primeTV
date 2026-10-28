#!/usr/bin/env bash
# =============================================================================
# PrimeTV — normalisation des fins de ligne (checkout Windows / CRLF)
# -----------------------------------------------------------------------------
# Symptômes traités :
#   nginx   : "/docker-entrypoint.d/10-primetv-cert.sh: not found"
#   backend : "env: use -[v]S to pass options in shebang lines"
# Cause   : les scripts contiennent des fins de ligne CRLF ; le noyau lit
#           « #!/bin/sh\r » et ne trouve pas l'interpréteur.
#
# Usage :
#   ./scripts/fix-line-endings.sh          # convertit CRLF → LF (fichiers texte)
#   ./scripts/fix-line-endings.sh --check   # vérifie sans modifier (code 1 si CRLF)
# =============================================================================
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CHECK=0
[[ "${1:-}" == "--check" ]] && CHECK=1

# Fichiers concernés : scripts, Dockerfiles, configuration, sources.
TARGETS=(
  "backend" "docker" "scripts" "tests" "web/scripts" "web/public" "examples"
  "docker-compose.yml" ".env.example" "Makefile"
)
EXTENSIONS=("sh" "bash" "py" "yml" "yaml" "conf" "json" "md" "ts" "tsx" "css" "html" "sql" "m3u" "xml")
FILES=()
while IFS= read -r file; do FILES+=("$file"); done < <(
  {
    find "${TARGETS[@]}" -type f 2>/dev/null
  } | while IFS= read -r file; do
    case "$file" in
      */node_modules/*|*/.venv/*|*/dist/*|*/certs/*.crt|*/certs/*.key|*.png|*.jpg|*.ico|*.woff|*.woff2) continue ;;
    esac
    base="$(basename "$file")"
    case "$base" in
      Dockerfile|Dockerfile.*|docker-entrypoint.sh|*.m3u|*.md) printf '%s\n' "$file"; continue ;;
    esac
    for ext in "${EXTENSIONS[@]}"; do
      [[ "$file" == *".$ext" ]] && { printf '%s\n' "$file"; break; }
    done
  done
)

FOUND=0
for file in "${FILES[@]}"; do
  if grep -qU $'\r' "$file" 2>/dev/null; then
    FOUND=$((FOUND + 1))
    if (( CHECK )); then
      echo "  ✘ CRLF : $file"
    else
      sed -i 's/\r$//' "$file"
      echo "  ✓ converti : $file"
    fi
  fi
done

if (( CHECK )); then
  if (( FOUND > 0 )); then
    echo ""
    echo "$FOUND fichier(s) en CRLF. Lancez : ./scripts/fix-line-endings.sh"
    exit 1
  fi
  echo "✓ Tous les fichiers texte sont en LF."
  exit 0
fi

if (( FOUND == 0 )); then
  echo "✓ Aucun fichier en CRLF : rien à faire."
else
  echo ""
  echo "$FOUND fichier(s) normalisés en LF."
  echo "Pour éviter que Git ne réintroduise des CRLF : git config core.autocrlf input"
fi

if command -v docker >/dev/null 2>&1 && (( FOUND > 0 )); then
  echo "→ Reconstruisez les images : docker compose build --no-cache backend nginx web"
fi
