# =============================================================================
# PrimeTV — application Flutter (build Web servi par Nginx)
#   docker build -t primetv-mobile --build-arg API_BASE_URL=/api/v1 .
# =============================================================================
FROM ghcr.io/cirruslabs/flutter:stable AS builder

WORKDIR /app
ARG API_BASE_URL=/api/v1
ENV API_BASE_URL=${API_BASE_URL}

COPY pubspec.yaml analysis_options.yaml ./
RUN flutter pub get

COPY . .
# La base href permet de servir l'app sous /mobile/
RUN flutter build web --release --base-href /mobile/ \
    --dart-define=API_BASE_URL=${API_BASE_URL}

FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
CMD ["nginx", "-g", "daemon off;"]
