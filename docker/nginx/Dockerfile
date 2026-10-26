# =============================================================================
# PrimeTV — reverse proxy d'entrée (Nginx + TLS local)
# -----------------------------------------------------------------------------
# Pourquoi une image dédiée plutôt que `image: nginx:1.27-alpine` + montages ?
#
#   1. Aucune dépendance aux permissions du système de fichiers hôte : le
#      script de certificat est copié dans l'image et marqué exécutable (sur un
#      checkout Windows, un fichier monté peut être non exécutable).
#   2. Protection contre les fins de ligne CRLF : `sed` retire les \r des
#      fichiers copiés. Avec CRLF, le noyau lit « #!/bin/sh\r » et échoue avec
#      « /docker-entrypoint.d/10-primetv-cert.sh: not found ».
#   3. Le client `openssl` (absent de nginx:alpine) est installé pour générer
#      le certificat auto-signé au premier démarrage.
# =============================================================================
FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="PrimeTV — Nginx" \
      org.opencontainers.image.description="Reverse proxy HTTP/2 + TLS du projet PrimeTV" \
      org.opencontainers.image.licenses="MIT"

# openssl : génération du certificat auto-signé ; curl : healthcheck.
RUN apk add --no-cache openssl curl tzdata \
    && rm -f /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/nginx.conf
COPY primetv_proxy_params.conf /etc/nginx/primetv_proxy_params.conf
COPY 10-generate-cert.sh /docker-entrypoint.d/10-primetv-cert.sh

# Normalisation LF + droits d'exécution (idempotent), puis validation de la config.
RUN sed -i 's/\r$//' /etc/nginx/nginx.conf /etc/nginx/primetv_proxy_params.conf \
        /docker-entrypoint.d/10-primetv-cert.sh \
    && chmod 0644 /etc/nginx/nginx.conf /etc/nginx/primetv_proxy_params.conf \
    && chmod 0755 /docker-entrypoint.d/10-primetv-cert.sh \
    && mkdir -p /etc/nginx/certs

# -----------------------------------------------------------------------------
# Validation de la configuration AU BUILD
# -----------------------------------------------------------------------------
# Deux obstacles à `nginx -t` pendant la construction de l'image :
#   1. les certificats TLS n'existent pas encore  → on en génère un jeu jetable ;
#   2. les `upstream` (backend:8000, web:80) ne sont pas résolubles pendant le
#      build (les conteneurs n'existent pas) → nginx répond
#      « host not found in upstream "backend:8000" » et échoue.
#
# On valide donc une COPIE temporaire de la configuration où les amonts Docker
# sont remplacés par des adresses locales : la syntaxe, les `location`, les
# modules, les `limit_req_zone` et les chemins de certificats sont vérifiés
# exactement comme en production, sans dépendre du DNS de Docker Compose.
RUN mkdir -p /etc/nginx/certs \
    && openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
        -keyout /etc/nginx/certs/primetv.key -out /etc/nginx/certs/primetv.crt \
        -subj "/CN=localhost" >/dev/null 2>&1 \
    && sed -e 's/server backend:8000;/server 127.0.0.1:8000;/' \
           -e 's/server web:80;/server 127.0.0.1:8080;/' \
           /etc/nginx/nginx.conf > /tmp/nginx-build-check.conf \
    && nginx -t -c /tmp/nginx-build-check.conf \
    && rm -f /tmp/nginx-build-check.conf /etc/nginx/certs/primetv.key /etc/nginx/certs/primetv.crt \
    && echo "Configuration Nginx validée (amonts Docker neutralisés pour le test)"

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/nginx-health >/dev/null 2>&1 || exit 1

# Le point d'entrée officiel de l'image nginx exécute /docker-entrypoint.d/*.sh
# (dont notre génération de certificat) avant de lancer Nginx.
CMD ["nginx", "-g", "daemon off;"]
