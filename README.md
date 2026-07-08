# Agent Tuteur Sénégal

Agent tuteur pédagogique **RAG + outils** pour le programme scolaire
sénégalais (préscolaire → Baccalauréat), à posture **socratique** : l'agent
guide l'élève vers la réponse par des indices progressifs plutôt que de la
donner directement, s'appuie sur un corpus curriculaire officiel filtré par
taxonomie (niveau/série/discipline), et sait déléguer le calcul à un outil
symbolique.

## Structure du dépôt

```
agent-tuteur-api/       Cœur métier + API FastAPI + worker ARQ
agent-tuteur-frontend/  Client Streamlit (aucun accès direct au cœur)
agent-tuteur-deploy/    docker-compose (dev/prod), nginx, scripts
docs/                   architecture.md, api.md, adr/, migration.md
```

## Architecture (résumé)

Le **cœur métier** (`agent/`, `vectorstore/`, `ingestion/`, `tools/`,
`config/`, `domain/`, sous `agent-tuteur-api/src/agent_tuteur/`) ne dépend
d'aucun framework web ni de base de données — il est testable et exécutable
hors-ligne (LLM mock, vectorstore in-memory). `api/` (FastAPI), `workers/`
(ARQ) et `persistence/` (PostgreSQL) sont aux extrémités et consomment ce
cœur. Le frontend Streamlit ne parle qu'HTTP/SSE à l'API.

Détails complets : [`docs/architecture.md`](docs/architecture.md) (composants,
flux RAG streamé, ingestion asynchrone, isolation multi-tenant),
[`docs/api.md`](docs/api.md) (chaque endpoint), [`docs/adr/`](docs/adr/)
(décisions techniques), [`docs/migration.md`](docs/migration.md).

## Prérequis

- Python 3.11+
- PostgreSQL 16, Redis 7 — et Qdrant si `VECTOR_BACKEND=qdrant` (recommandé
  dès qu'un worker d'ingestion tourne séparément de l'API, cf. limitation
  ci-dessous)
- Docker + Docker Compose (pour `agent-tuteur-deploy/`)

## Démarrage rapide — Docker Compose (recommandé)

```bash
cd agent-tuteur-deploy
docker compose -f docker-compose.dev.yml up -d --build
```

Démarre Postgres, Redis, Qdrant, applique les migrations (`migrate`), puis
lance l'API (`:8000`), le worker ARQ, et le frontend Streamlit (`:8501`).

- API : http://localhost:8000/docs
- Frontend : http://localhost:8501
- Health check : http://localhost:8000/health

Pour la production : `docker-compose.prod.yml` (secrets via `.env.prod`, nginx
en frontal avec SSL/rate limiting, aucun port interne exposé). Voir
`agent-tuteur-deploy/scripts/setup.sh` (certificat + `.env.prod` de départ) et
`scripts/deploy.sh`.

## Démarrage local (sans Docker)

```bash
make setup      # crée .venv, installe les dépendances (API + frontend)
make migrate    # applique les migrations Alembic (DATABASE_URL requis)
make dev        # lance api + worker + frontend en parallèle
```

Cibles individuelles : `make api`, `make worker`, `make run` (frontend),
`make test`, `make seed` (ingère le corpus d'exemple). Voir le `Makefile` pour
le détail de chaque cible et ses prérequis.

**Démo 100% hors-ligne** (sans Postgres/Redis/Qdrant, LLM mock, vectorstore
in-memory) :

```bash
cd agent-tuteur-api
PYTHONPATH=src python scripts/demo.py
```

## Variables d'environnement

Voir `agent-tuteur-api/.env.example` (backend : DB, Redis, Qdrant, LLM,
tenant, rate limiting) et `agent-tuteur-frontend/.env.example` (`API_BASE_URL`).
Tous les défauts permettent un fonctionnement dégradé sans infrastructure
lourde (backends légers, LLM mock) — voir la section « Dégradation gracieuse »
de `docs/architecture.md`.

⚠️ **RLS et rôle Postgres** : en production, `DATABASE_URL` de l'API/du worker
doit utiliser un rôle **non-superuser** (`postgres-init/01-app-role.sh` dans
`agent-tuteur-deploy/`) — un superuser Postgres contourne toujours le Row
Level Security, même avec `FORCE ROW LEVEL SECURITY`.

## Formats supportés

- **Corpus curriculaire** : PDF, DOCX, TXT, MD (upload via `POST /api/documents`).
- **Format pivot interne** : Markdown + LaTeX inline (`$...$`, `$$...$$`) — cf.
  [ADR 0007](docs/adr/0007-format-pivot-markdown-latex.md).

## Tests

```bash
cd agent-tuteur-api
python -m pytest -q
```

Suite complète (cœur + persistance + API + worker), avec skip automatique des
tests nécessitant Postgres/Redis réels si `TEST_DATABASE_URL`/`TEST_REDIS_URL`
ne sont pas définis — voir `agent-tuteur-api/README.md` pour le détail.

## Limitation connue

Avec `VECTOR_BACKEND=memory` (défaut hors-ligne) **et** un worker ARQ dans un
processus séparé de l'API, chaque processus a son propre store en mémoire : un
document ingéré par le worker n'est pas visible en recherche côté API. Utiliser
`VECTOR_BACKEND=qdrant` (configuration par défaut de `docker-compose.dev.yml`)
dès qu'un worker séparé est utilisé — validé en conditions réelles (voir
[ADR 0002](docs/adr/0002-qdrant-plus-postgres.md) et
[ADR 0004](docs/adr/0004-ingestion-asynchrone-arq.md)).
