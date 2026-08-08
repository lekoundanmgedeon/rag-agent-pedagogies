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

## Installation complète

```bash
pip install -r requirements.txt      # versions exactes validées
pip install -e '.[parsing,dev]'      # PyMuPDF + ruff
```

⚠️ **L'extra `parsing` n'est pas facultatif en pratique.** Sans PyMuPDF, la
lecture des PDF retombe sur `pypdf`, qui **aplatit ou perd** fractions, indices
et exposants et se trompe souvent sur l'ordre de lecture des colonnes. Le corpus
visé étant à 100 % des mathématiques du secondaire, le repli abîme le contenu
sans rien casser visiblement — seule une ligne de journal le signale. Le repli
existe parce qu'une dépendance optionnelle manquante ne doit jamais faire
échouer une ingestion, pas parce que `pypdf` conviendrait.

Autres extras déclarés dans `pyproject.toml` : `embeddings` (BGE-M3),
`vectorstore` (Qdrant), `persistence` (PostgreSQL + Alembic), `api` (FastAPI),
`auth` (JWT + bcrypt), `worker` (ARQ + Redis).

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
chaque endpoint : `../docs/api.md`. Tous les modes de lancement (Docker,
hybride, tout local) : `../docs/GUIDE_LANCEMENT.md`.

### ⚠️ Après toute modification d'une route ou d'un schéma

Le schéma OpenAPI est **versionné** (`openapi.json`) : c'est le contrat dont le
frontend Next.js dérive ses types TypeScript. Régénérer les deux :

```bash
python scripts/export_openapi.py openapi.json
cd ../agent-tuteur-web-next && npm run gen:api
```

L'intégration continue régénère et exige zéro différence — elle échoue sinon.
C'est ce qui fait que renommer un champ ici **casse la compilation** du frontend
au lieu de passer inaperçu jusqu'en production.

## Tests

```bash
PYTHONPATH=src python -m pytest -q          # depuis ce répertoire, pas la racine
```

État de référence : **317 passés, 98 ignorés** sans infrastructure.

Les tests du cœur (config/ingestion/vectorstore/agent/domaine) tournent toujours.
Ceux de persistance, d'API et de worker s'auto-skip si `TEST_DATABASE_URL` /
`TEST_REDIS_URL` ne sont pas définis :

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://tuteur:tuteur@localhost:5432/tuteur
export TEST_REDIS_URL=redis://localhost:6379/0
PYTHONPATH=src python -m pytest -q          # 413 tests
```

⚠️ Les 98 tests ignorés ne sont pas anodins : ils comprennent **tous les tests de
contrôle d'accès**. Ne jamais conclure « tout passe » sur la seule foi des 317 —
c'est pourquoi l'intégration continue démarre un vrai service PostgreSQL.

⚠️ Lancer `pytest` **depuis la racine du dépôt** fait échouer ~26 tests en
cascade (config et environnement introuvables depuis ce répertoire de travail).

Analyse statique, telle que la CI l'exécute :

```bash
ruff check .        # doit afficher : All checks passed!
```

## Organisation (framework-agnostique au cœur)

| Module | Rôle |
|---|---|
| `config/` | réglages (`settings`) + taxonomie curriculaire (`taxonomy`) |
| `domain/` | modèles partagés (`models`) + règles de maîtrise progressive (`mastery`) |
| `ingestion/` | `loaders/` (PDF PyMuPDF + extracteurs de métadonnées), normalisation (format pivot), chunking, annotation, `consistency` (détection des documents orphelins) |
| `vectorstore/` | embeddings, store (in-memory/Qdrant), indexer, retriever hybride + re-ranking cours/complément |
| `tools/` | calculatrice symbolique SymPy en sandbox |
| `agent/` | `intent` (aiguillage exercice/cours), `hint_strategy` + `frustration` (posture socratique), `course_plan` (mode cours), `quiz` + `verify` (mode quiz), `llm/` (chaîne de repli), `guardrails`, graphe LangGraph |
| `persistence/` | modèles ORM + repositories PostgreSQL (implémentent `agent/ports.py`) |
| `api/` | routes FastAPI, dépendances (dont la règle d'accès centralisée), streaming SSE, rate limiting, lifespan |
| `workers/` | worker ARQ (ingestion asynchrone) |

Le cœur (`agent/`, `vectorstore/`, `ingestion/`, `tools/`, `config/`, `domain/`)
ne dépend d'aucun framework web ni d'aucune base de données : il est testable et
exécutable hors-ligne. `api/`, `workers/` et `persistence/` sont aux extrémités
et le consomment.

### Les trois postures de l'agent

| Posture | Comportement | Aiguillage |
|---|---|---|
| **exercice** *(défaut)* | Indices gradués 0-4, l'agent retient volontairement le contenu | défaut en cas d'ambiguïté — ne jamais dériver hors de ce mode par accident |
| **cours** | Exposé didactique, section par section (progression curée de 8 étapes) | `agent/intent.py`, heuristique regex, sans appel LLM |
| **quiz** | Interroge, vérifie de façon déterministe, enregistre la maîtrise | routes `/api/quiz` |

## Scripts

| Script | Rôle |
|---|---|
| `scripts/demo.py` | démo hors-ligne de bout en bout (aussi `make seed`) |
| `scripts/create_user.py` | crée un compte — `--role admin\|student` **seulement** (voir ci-dessous) |
| `scripts/export_openapi.py` | régénère `openapi.json` — obligatoire après toute modification de route |
| `scripts/seed_corpus.py` | téléverse `corpus/` via `POST /api/documents` (même pipeline qu'un upload admin) ; idempotent, conçu comme service one-shot du compose de dev |

> ⚠️ **Écart connu, non corrigé** : la migration `0007` a étendu les rôles à
> `teacher` et `parent`, et `POST /api/auth/users` les accepte
> (`api/schemas.py`), mais `scripts/create_user.py` est resté sur
> `choices=["admin", "student"]`. Un compte enseignant ou parent ne peut donc
> être créé **que par l'API**, pas en ligne de commande. À aligner — c'est une
> modification de code, pas de documentation.

## Migrations

`migrations/versions/` — sept révisions Alembic. Les deux dernières viennent de
la fusion : `0006_pedagogical_progress` (maîtrise, résultats d'exercices,
badges, recommandations, liaisons parent/enseignant→élève, toutes sous RLS) et
`0007_extend_roles` (rôles `teacher` et `parent` en plus de `admin` et
`student`).

Les migrations sont traitées comme des **archives** : une fois appliquées en
production, leur contenu ne bouge plus (d'où leur exclusion partielle des règles
ruff).

Voir `../docs/architecture.md` pour la spécification complète des flux et des
frontières de responsabilité.
