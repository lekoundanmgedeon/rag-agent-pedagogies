# agent-tuteur-api

Cœur métier + API de l'agent tuteur pédagogique RAG pour le programme scolaire
sénégalais. Voir le README à la racine du dépôt pour la vue d'ensemble multi-
service ; ce document couvre spécifiquement ce sous-projet.

## Démo hors-ligne (sans infrastructure)

```bash
python3 -m venv .venv && source .venv/bin/activate   # ou get-pip si ensurepip absent
pip install -r requirements.txt
PYTHONPATH=src python scripts/demo.py
```

Ingeste le corpus d'exemple (`corpus/`) dans un vectorstore in-memory puis pose
une question à l'agent (mode LLM *mock*), en affichant le niveau d'indice, les
sources RAG et la réponse streamée.

## API complète (Postgres + Redis requis)

```bash
export DATABASE_URL=postgresql+asyncpg://tuteur_app:...@localhost:5432/tuteur
export REDIS_URL=redis://localhost:6379/0
alembic upgrade head
PYTHONPATH=src uvicorn agent_tuteur.api.main:app --reload
# dans un autre terminal :
PYTHONPATH=src python -m arq agent_tuteur.workers.ingestion_worker.WorkerSettings
```

Documentation OpenAPI interactive : `http://localhost:8000/docs`. Détail de
chaque endpoint : `../docs/api.md`.

## Tests

```bash
PYTHONPATH=src python -m pytest -q
```

Sans infrastructure : les tests du cœur (config/ingestion/vectorstore/agent)
tournent toujours. Les tests de persistance/API/worker nécessitant Postgres ou
Redis réels s'auto-skip si `TEST_DATABASE_URL`/`TEST_REDIS_URL` ne sont pas
définis :

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://tuteur:tuteur@localhost:5432/tuteur
export TEST_REDIS_URL=redis://localhost:6379/0
PYTHONPATH=src python -m pytest -q
```

## Organisation (framework-agnostique au cœur)

| Module | Rôle |
|---|---|
| `config/` | réglages (`settings`) + taxonomie curriculaire (`taxonomy`) |
| `domain/` | modèles partagés (`CurriculumMetadata`, `Chunk`, `ScoredChunk`) |
| `ingestion/` | loaders, normalisation (format pivot), chunking, annotation |
| `vectorstore/` | embeddings, store (in-memory/Qdrant), indexer, retriever hybride |
| `tools/` | calculatrice symbolique SymPy en sandbox |
| `agent/` | stratégie d'indice, frustration, LLM+fallback, garde-fous, graphe LangGraph |
| `persistence/` | modèles ORM + repositories PostgreSQL (implémentent `agent/ports.py`) |
| `api/` | routes FastAPI, dépendances, streaming SSE, lifespan |
| `workers/` | worker ARQ (ingestion asynchrone) |

Voir `../docs/architecture.md` pour la spécification complète des flux et
frontières de responsabilité.
