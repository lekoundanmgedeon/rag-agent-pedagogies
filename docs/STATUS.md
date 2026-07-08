# État d'avancement — agent-tuteur-senegal

_Dernière mise à jour : 2026-07-08. Document de reprise de session — pas une doc finale._

## Où on en est

Étapes **1 à 4 terminées et testées**. Étape **5 (API FastAPI) en cours**,
code écrit mais **pas encore testé** (aucun test API n'a encore été lancé,
l'app n'a pas encore démarré). C'est le point de reprise.

Périmètre convenu avec l'utilisateur : construire 1→8, s'arrêter après l'étape 5
pour validation avant de continuer vers 6-8 (ARQ, Streamlit, déploiement).

## Environnement

- Repo local (pas de git initialisé) : `/home/aimssn/nuru/rag-agent-pedagogie/`
- Code applicatif : `agent-tuteur-api/` (package Python `agent_tuteur`, layout `src/`)
- Venv : `/home/aimssn/nuru/rag-agent-pedagogie/.venv/` (bootstrappé manuellement
  car `python3 -m venv` n'a pas `ensurepip` sur cette machine — utiliser
  `.venv/bin/python -m pip ...` directement, pas de `source activate`).
- **Postgres de test jetable** : conteneur Docker `tutor-senegal-pg-test`
  (image `postgres:16-alpine`), port hôte **55432**, db/user/password = `tuteur`.
  Lancé via :
  ```bash
  docker run -d --name tutor-senegal-pg-test \
    -e POSTGRES_USER=tuteur -e POSTGRES_PASSWORD=tuteur -e POSTGRES_DB=tuteur \
    -p 55432:5432 postgres:16-alpine
  ```
  ⚠️ Ne pas confondre avec les conteneurs `rag-api-db-1` / `rag-api-redis-1`
  déjà présents sur la machine (Docker `docker ps`) — appartiennent à un **autre
  projet**, ne pas y toucher.
- Migrations déjà appliquées sur ce conteneur (`alembic upgrade head`).
- Rôle non-superuser `app_user`/`app_pw` créé sur ce Postgres de test pour
  valider que RLS fonctionne réellement (le rôle par défaut `tuteur` est
  superuser dans l'image officielle Postgres et **contourne toujours RLS**,
  même avec `FORCE ROW LEVEL SECURITY` — piège documenté dans `.env.example`).

## Ce qui est fait et testé (étapes 1-4)

### Étape 1 — Squelette
- `config/settings.py` (pydantic-settings), `config/taxonomy.py` (niveaux,
  examens, classes d'équivalence de séries avec alias : `T1↔STIDD1`, `G↔STEG`…)
- `domain/models.py` : `CurriculumMetadata`, `Chunk`, `ScoredChunk`
- 5 documents corpus `.md` annotés dans `agent-tuteur-api/corpus/`
- `pyproject.toml`, `requirements.txt`, `.env.example`

### Étape 2 — Cœur RAG + ingestion
- Embeddings hybrides : léger déterministe (défaut) + BGE-M3 (lazy)
- Store : in-memory (RRF, filtrage + alias série) + Qdrant (lazy, **sync** —
  limitation connue, cf. section "Dettes/limitations" plus bas)
- `indexer`, `retriever`, pipeline d'ingestion (loaders/normalize/chunking
  structurel/annotation)

### Étape 3 — Agent
- `tools/calculator.py` (SymPy sandbox), `frustration.py`, `hint_strategy.py`
  (échelle 0→4), `guardrails.py` (sanitize anti-injection, modération, clamp)
- LLM : `BaseLLM`/`MistralLLM`/`OllamaLLM`/`MockLLM`/`FallbackRouter`
- Graphe LangGraph 6 nœuds + façade `TutorAgent` (`prepare`/`stream`/`respond`)

### Refactor async (fait entre étape 3 et 4, nécessaire pour Postgres+FastAPI)
**Tout le cœur agent est maintenant async** :
- `agent/ports.py` : `StudentMemoryPort`/`AuditLogPort` sont des `Protocol` **async**
- `agent/llm/*.py` : `generate`/`generate_stream` sont async (`AsyncIterator`,
  `httpx.AsyncClient`). `available()` reste sync (probe de démarrage seulement).
- `agent/graph.py` : nœuds = coroutines, graphes invoqués via `ainvoke`.
  **Point clé** : `memory`/`audit` peuvent être injectés soit à la construction
  de `TutorAgent` (démo/tests), soit **par appel** à `prepare()`/`respond()`
  (kwargs `memory=`/`audit=`) — c'est ce qui permet à l'API de passer des
  repositories Postgres liés à la session de **chaque requête** sans reconstruire
  le graphe (coûteux) à chaque fois.
- `agent/state.py` : le champ `audit` a été **renommé `node_trace`** (c'était le
  journal interne des nœuds LangGraph, homonyme confus avec `AuditLogPort`).
  Nouveaux champs `memory_port`/`audit_port` dans `AgentState`.
  ⚠️ Piège rencontré : `StudentMemoryPort`/`AuditLogPort` doivent être importés
  **normalement** (pas seulement sous `TYPE_CHECKING`) dans `state.py`, car
  LangGraph résout les annotations du `TypedDict` au runtime.
- Tous les tests + `scripts/demo.py` mis à jour en async en conséquence.

### Étape 4 — Persistance PostgreSQL + Alembic
- `persistence/db.py` : engine/session async, `session_scope(tenant_id)`
  (context manager avec commit/rollback auto + `set_tenant_context` pour RLS)
- `persistence/models.py` : 6 tables (`progress`, `audit_log`, `conversations`,
  `messages`, `feedback`, `documents`), **tenant_id sur TOUTES** (y compris
  `messages`/`feedback`, dénormalisé — écart assumé par rapport au prompt
  original qui ne les listait pas avec tenant_id, corrigé pour cohérence avec
  le principe "tenant_id partout" + simplifier RLS sans jointure)
  - UUID via `sqlalchemy.Uuid(as_uuid=False)` (portable sqlite/postgres)
  - JSON via `JSON().with_variant(JSONB(), "postgresql")` (JSONB en prod, JSON
    générique en test SQLite)
  - `Document.metadata_` (attribut Python renommé, colonne DB reste `metadata`
    — `metadata` est réservé par `Base.metadata` en SQLAlchemy déclaratif)
- `persistence/repositories.py` : `ProgressRepository`/`AuditLogRepository`
  (implémentent les ports du cœur agent) + `ConversationRepository`/
  `MessageRepository`/`FeedbackRepository`/`DocumentRepository` (pour l'API)
- Migrations Alembic (`migrations/versions/`) :
  - `0001_initial_schema.py` (auto-générée puis nettoyée)
  - `0002_enable_rls.py` (RLS + `FORCE ROW LEVEL SECURITY` + policy
    `tenant_isolation` sur les 6 tables, no-op si dialecte ≠ postgresql)
  - `migrations/env.py` modifié : importe `Base`/`models`, lit l'URL depuis
    `get_settings().database_url` (pas depuis `alembic.ini`)
- Tests (`tests/persistence/`) :
  - `test_repositories.py` : SQLite in-memory (aiosqlite), toujours exécutés
  - `test_postgres_smoke.py` + `test_agent_with_postgres.py` : contre Postgres
    réel, **skip automatique** si `TEST_DATABASE_URL` non défini/injoignable
  - Pour relancer contre le conteneur de test :
    ```bash
    export TEST_DATABASE_URL="postgresql+asyncpg://tuteur:tuteur@localhost:55432/tuteur"
    ```

**Total tests à la fin de l'étape 4 : 79 passed** (74 sans Postgres dispo, 4 skip).

## Étape 5 — API FastAPI (EN COURS, pas encore testée)

### Fait
- `config/settings.py` : ajout `cors_origins`, `rate_limit_chat`, `rate_limit_upload`
- `api/schemas.py` : tous les modèles Pydantic de requête/réponse
- `api/dependencies.py` : `get_tenant_id` (header `X-Tenant-Id`), `get_session`
  (session par requête, **non utilisée telle quelle pour le chat streamé** —
  voir plus bas), repositories, `get_agent`/`get_indexer`/`get_retriever`
  (lus depuis `app.state`, posés par le `lifespan` — **le lifespan n'est pas
  encore écrit**, c'est la prochaine étape)
- `api/rate_limit.py` : instance unique `Limiter` (slowapi) partagée
- `api/streaming.py` : helper `sse_event()`
- `api/routes/chat.py` : **POST /api/chat** complet
  - `sanitize()` appelé HORS du générateur (pour pouvoir renvoyer un vrai 400
    avant de créer le `StreamingResponse` — le status code ne peut plus changer
    une fois le flux commencé)
  - Session DB ouverte manuellement via `session_scope()` **dans le générateur**
    (pas via `Depends(get_session)`, qui se fermerait au retour de la fonction
    de route alors que le générateur continue après)
  - Contrat SSE : `{meta}` → `{token}*` → `{done: {message_id, conversation_id}}`
  - Persistance conversation/messages **après** la fin du stream de tokens mais
    **avant** l'event `done` (car `done` contient `message_id`)
- `api/routes/documents.py` : upload, list, get, delete, status (SSE polling),
  reindex — **écrit mais jamais exécuté/testé**. Décisions à relire :
  - Ingestion post-upload via `BackgroundTasks` (PAS ARQ, qui est étape 6) —
    documenté en commentaire de module comme substitut temporaire, même code
    de pipeline réutilisé tel quel
  - `/status` : SSE par **sondage** DB toutes les 500ms (pas d'événements fins
    par étape extract/normalize/chunk — viendra avec le worker ARQ)
  - `/reindex` accepte un **nouveau fichier** (pas de blob storage dans la
    stack verrouillée pour conserver le fichier original) — écart documenté
    par rapport au prompt initial, à justifier dans un ADR
  - Ajout de `Indexer.delete_source()` (méthode publique) pour éviter d'accéder
    à `indexer._store` depuis les routes (encapsulation)

### PAS FAIT — prochaines actions immédiates
1. **`api/routes/search.py`** (POST /api/search) — pas commencé
2. **`api/routes/progression.py`** (GET /api/progression/{student_id}) — pas commencé
3. **`api/routes/feedback.py`** (POST /api/messages/{id}/feedback) — pas commencé
4. **`api/routes/health.py`** (GET /health) — pas commencé
5. **`api/main.py`** — PAS ÉCRIT. Doit contenir :
   - `lifespan` : `init_engine(settings.database_url)`, construire
     `build_rag_stack()` + `build_llm()` + `TutorAgent` et les poser sur
     `app.state.{indexer,retriever,agent}`, `dispose_engine()` à l'arrêt
   - `app.state.limiter = limiter` + exception handler `RateLimitExceeded`
   - `CORSMiddleware` (origins depuis `settings.cors_origin_list`)
   - `include_router()` pour chat/documents/search/progression/feedback/health
6. **Tests API** (`tests/api/`, dossier créé mais vide) — à écrire avec
   `TestClient`/`httpx.AsyncClient` + `ASGITransport`, en overridant les
   dépendances (`app.dependency_overrides`) pour utiliser SQLite in-memory ou
   le Postgres de test selon les cas
7. **Vérifier `upload_documents`** : signature corrigée en dernier avec
   `File(...)`/`Form(...)` mais **jamais testée** — première chose à valider
   une fois `main.py` écrit
8. Une fois l'API démarrable : tester manuellement avec `uvicorn` + `curl`
   (chat streaming, upload, etc.) avant de considérer l'étape 5 terminée

## Dettes / limitations connues (à mentionner à l'utilisateur, pas à cacher)

- **Qdrant store est synchrone** (`vectorstore/qdrant_store.py` utilise
  `QdrantClient` sync, pas `AsyncQdrantClient`). Avec `VECTOR_BACKEND=memory`
  (défaut) aucun souci (calcul CPU pur, rapide). Si un jour on bascule sur
  Qdrant réel, les appels bloqueraient la boucle événementielle FastAPI.
  Non corrigé (hors périmètre demandé), à signaler.
- **Redis/ARQ non câblés** : `GET /health` devra reporter `redis` comme
  `"not_configured"` plutôt que de tenter une vraie connexion.
- **RLS et superuser** : bien retenir/redire à l'utilisateur que le
  `DATABASE_URL` de production doit pointer vers un rôle **non-superuser**
  sans quoi les policies RLS ne servent à rien (déjà documenté dans
  `.env.example` et l'ADR à écrire).

## Commandes utiles pour reprendre

```bash
# Activer les deps (déjà installées dans le venv)
VENV=/home/aimssn/nuru/rag-agent-pedagogie/.venv/bin/python

# Lancer les tests (avec Postgres de test si le conteneur tourne encore)
cd /home/aimssn/nuru/rag-agent-pedagogie/agent-tuteur-api
export TEST_DATABASE_URL="postgresql+asyncpg://tuteur:tuteur@localhost:55432/tuteur"
$VENV -m pytest -q

# Vérifier que le conteneur Postgres de test tourne toujours
docker ps --filter name=tutor-senegal-pg-test

# Si besoin de le relancer (les données de test seront reperdues, refaire les migrations) :
docker start tutor-senegal-pg-test   # ou re-créer avec la commande docker run plus haut
export DATABASE_URL="postgresql+asyncpg://tuteur:tuteur@localhost:55432/tuteur"
$VENV -m alembic upgrade head
```

## Fichiers écrits jusqu'ici (étape 5, pour retrouver rapidement)

```
src/agent_tuteur/api/
├── __init__.py
├── schemas.py            (fait)
├── dependencies.py        (fait)
├── rate_limit.py          (fait)
├── streaming.py            (fait)
├── main.py                 ← À ÉCRIRE (prochaine étape)
└── routes/
    ├── __init__.py
    ├── chat.py             (fait)
    ├── documents.py        (fait, non testé)
    ├── search.py           ← À ÉCRIRE
    ├── progression.py      ← À ÉCRIRE
    ├── feedback.py         ← À ÉCRIRE
    └── health.py           ← À ÉCRIRE
tests/api/                  (dossier créé, vide — tests à écrire)
```
