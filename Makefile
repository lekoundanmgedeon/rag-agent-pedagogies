# Cibles de développement local (sans Docker) — pour la stack conteneurisée,
# voir agent-tuteur-deploy/ (docker-compose.dev.yml / .prod.yml).
#
# Prérequis : PostgreSQL, Redis (et Qdrant si VECTOR_BACKEND=qdrant) déjà
# lancés et accessibles via les variables de agent-tuteur-api/.env.

API_DIR := agent-tuteur-api
WEB_DIR := agent-tuteur-web
VENV := .venv/bin

.PHONY: setup migrate api worker run dev test seed createadmin lint clean

setup: ## Crée le venv (API) et installe les dépendances (API Python + frontend npm).
	python3 -m venv .venv
	$(VENV)/pip install --upgrade pip
	$(VENV)/pip install -r $(API_DIR)/requirements.txt -e $(API_DIR)
	cd $(WEB_DIR) && npm install

migrate: ## Applique les migrations Alembic (nécessite DATABASE_URL valide).
	cd $(API_DIR) && ../$(VENV)/python -m alembic upgrade head

api: ## Démarre l'API FastAPI (uvicorn, rechargement à chaud).
	cd $(API_DIR) && PYTHONPATH=src ../$(VENV)/python -m uvicorn agent_tuteur.api.main:app --reload --host 0.0.0.0 --port 8000

worker: ## Démarre le worker ARQ (ingestion asynchrone).
	cd $(API_DIR) && PYTHONPATH=src ../$(VENV)/python -m arq agent_tuteur.workers.ingestion_worker.WorkerSettings

run: ## Démarre le frontend web Vue (Vite, proxy /api -> :8000).
	cd $(WEB_DIR) && npm run dev

createadmin: ## Crée un compte admin (EMAIL=... PASSWORD=... [TENANT=default]).
	cd $(API_DIR) && ../$(VENV)/python scripts/create_user.py \
		--email "$(EMAIL)" --password "$(PASSWORD)" --role admin --tenant "$(or $(TENANT),default)"

dev: ## Lance api + worker + frontend en parallèle (arrêt : Ctrl+C).
	$(MAKE) -j3 api worker run

test: ## Lance la suite de tests (skip auto si Postgres/Redis de test absents).
	cd $(API_DIR) && ../$(VENV)/python -m pytest -q

seed: ## Ingeste le corpus d'exemple dans le vectorstore configuré.
	cd $(API_DIR) && PYTHONPATH=src ../$(VENV)/python scripts/demo.py

clean: ## Supprime le venv et les caches Python.
	rm -rf .venv $(API_DIR)/.pytest_cache $(API_DIR)/**/__pycache__
