# =============================================================================
# PrimeTV — raccourcis de développement et d'exploitation
# -----------------------------------------------------------------------------
#   make help        liste les commandes disponibles
#   make up          démarre la pile Docker Compose
#   make dev         API + front-end en local (sans Docker)
#   make test        lint + tests backend/frontend + PWA + smoke API
#   make fix-eol     convertit les CRLF en LF (checkout Windows)
# =============================================================================
SHELL := /bin/bash
.DEFAULT_GOAL := help
ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
COMPOSE := docker compose
PY := backend/.venv/bin/python
PIP := backend/.venv/bin/pip

.PHONY: help install up down restart logs ps build pull status \
        dev api web test test-backend test-web test-api lint fix-eol \
        backup restore health clean shell-db shell-api

help: ## Affiche cette aide
	@echo "PrimeTV — commandes disponibles :"
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --------------------------------------------------------------- installation
install: ## Installation complète (secrets, images, démarrage)
	./scripts/install.sh

up: ## Démarre la pile (build si nécessaire)
	$(COMPOSE) up -d --build

down: ## Arrête la pile
	$(COMPOSE) down

restart: ## Redémarre la pile
	$(COMPOSE) restart

build: ## Reconstruit toutes les images
	$(COMPOSE) build

ps: ## État des conteneurs
	$(COMPOSE) ps

status: ps ## Alias de `make ps`

logs: ## Journaux en continu (SERVICE=backend pour cibler)
	$(COMPOSE) logs -f $(SERVICE)

pull: ## Met à jour les images de base et le code
	./scripts/update.sh

# --------------------------------------------------------------- développement
dev: ## API (:8000) + Vite (:5173) en local
	./scripts/dev.sh

api: ## Lance uniquement l'API en local (rechargement auto)
	cd backend && DATABASE_URL=$${DATABASE_URL:-sqlite:///./primetv_local.db} \
		SEED_DEMO_DATA=$${SEED_DEMO_DATA:-true} \
		.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web: ## Lance uniquement le front-end (Vite, :5173)
	cd web && npm run dev

shell-api: ## Ouvre un shell dans le conteneur backend
	$(COMPOSE) exec backend /bin/sh

shell-db: ## Ouvre psql sur la base
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-primetv} -d $${POSTGRES_DB:-primetv}

# ---------------------------------------------------------------------- tests
test: ## Suite complète (lint, tests, build, PWA, smoke API)
	./scripts/test-all.sh

test-backend: ## Tests backend (ruff + pytest)
	cd backend && .venv/bin/ruff check app tests && .venv/bin/python -m pytest -q

test-web: ## Tests frontend (typage, vitest, build, artefacts PWA)
	cd web && npm run lint && npm run test && npm run build

test-api: ## Smoke test de l'API démarrée
	./tests/api/smoke.sh

lint: ## Lint backend + typage frontend
	cd backend && .venv/bin/ruff check app tests
	cd web && npm run lint

fix-eol: ## Convertit les CRLF en LF (Windows) et vérifie les scripts
	./scripts/fix-line-endings.sh

# ------------------------------------------------------------------ exploitation
health: ## Vérifie l'état de la pile
	./scripts/healthcheck.sh

backup: ## Sauvegarde PostgreSQL
	./scripts/backup.sh

restore: ## Restaure une sauvegarde (--latest ou fichier)
	./scripts/restore.sh

clean: ## Supprime les artefacts de build locaux (dist, caches)
	rm -rf web/dist .pytest_cache backend/.pytest_cache backend/.ruff_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Artefacts nettoyés (node_modules et .venv conservés)."
