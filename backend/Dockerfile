# =============================================================================
# PrimeTV — image de l'API FastAPI (multi-étapes, non-root)
# =============================================================================
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app

RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system primetv \
    && useradd --system --gid primetv --home-dir ${APP_HOME} --shell /usr/sbin/nologin primetv

WORKDIR ${APP_HOME}
COPY --from=builder /opt/venv /opt/venv
COPY --chown=primetv:primetv app ./app
COPY --chown=primetv:primetv docker-entrypoint.sh ./docker-entrypoint.sh
# `sed 's/\r$//'` : sur un checkout Windows (CRLF), le noyau lit « #!/usr/bin/env sh\r »
# et échoue avec « env: use -[v]S to pass options in shebang lines ».
RUN sed -i 's/\r$//' ./docker-entrypoint.sh \
    && chmod 0755 ./docker-entrypoint.sh \
    && mkdir -p /app/data \
    && chown -R primetv:primetv /app

USER primetv
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "./docker-entrypoint.sh"]
CMD ["web"]
