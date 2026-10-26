#!/usr/bin/env bash
# Génère un certificat auto-signé pour l'entrée Nginx (développement / réseau privé).
set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docker/nginx/certs"
DOMAIN="${1:-localhost}"

mkdir -p "$CERT_DIR"
if [[ -f "$CERT_DIR/primetv.crt" ]]; then
  echo "→ Certificat déjà présent ($CERT_DIR/primetv.crt), rien à faire."
  exit 0
fi

openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout "$CERT_DIR/primetv.key" \
  -out "$CERT_DIR/primetv.crt" \
  -subj "/C=TN/ST=Tunis/L=Tunis/O=PrimeTV/CN=${DOMAIN}" \
  -addext "subjectAltName=DNS:${DOMAIN},DNS:localhost,IP:127.0.0.1"

chmod 600 "$CERT_DIR/primetv.key"
echo "✓ Certificat auto-signé généré pour ${DOMAIN}"
