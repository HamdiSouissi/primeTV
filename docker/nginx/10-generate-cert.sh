#!/bin/sh
# Génère un certificat auto-signé au premier démarrage du conteneur Nginx.
set -eu
CERT_DIR="/etc/nginx/certs"
if [ ! -f "$CERT_DIR/primetv.crt" ] || [ ! -f "$CERT_DIR/primetv.key" ]; then
  echo "[primetv] Génération d'un certificat auto-signé (TLS local)…"
  mkdir -p "$CERT_DIR"
  openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
    -keyout "$CERT_DIR/primetv.key" \
    -out "$CERT_DIR/primetv.crt" \
    -subj "/C=TN/ST=Tunis/L=Tunis/O=PrimeTV/CN=${PRIMETV_DOMAIN:-localhost}" \
    -addext "subjectAltName=DNS:${PRIMETV_DOMAIN:-localhost},DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
fi
