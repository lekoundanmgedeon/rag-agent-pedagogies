# Architecture — Agent Tuteur Sénégal

## 1. Vue d'ensemble

```
┌─────────────────────┐        ┌──────────────────────────────────────┐
│  agent-tuteur-       │  HTTP  │  agent-tuteur-api                    │
│  frontend            │◄──────►│  ┌────────────────────────────────┐ │
│  (Streamlit)          │  SSE   │  │ api/  (FastAPI, routes, deps)  │ │
└─────────────────────┘        │  └───────────────┬────────────────┘ │
                                 │                  │                  │
                                 │  ┌───────────────▼────────────────┐ │
                                 │  │ cœur métier (framework-agnostic)│ │
                                 │  │ agent/ vectorstore/ ingestion/  │ │
                                 │  │ tools/ config/ domain/          │ │
                                 │  └──┬──────────┬──────────┬───────┘ │
                                 │     │          │          │         │
                                 │ ┌───▼───┐ ┌────▼────┐ ┌──▼──────┐  │
                                 │ │persist.│ │workers/  │ │ (LLM,    │  │
                                 │ │(SQLAlch│ │(ARQ)     │ │ Qdrant)  │  │
                                 │ │async)  │ │          │ │ clients  │  │
                                 │ └───┬───┘ └────┬─────┘ └──────────┘  │
                                 └─────┼──────────┼──────────────────────┘
                                       │          │
                                 ┌─────▼──┐  ┌────▼───┐  ┌─────────┐
                                 │Postgres│  │ Redis  │  │ Qdrant  │
                                 └────────┘  └────────┘  └─────────┘
```

**Principe transversal** : `agent/`, `vectorstore/`, `ingestion/`, `tools/`,
`config/`, `domain/` (le « cœur ») ne dépendent **jamais** de FastAPI, de
SQLAlchemy côté logique métier, ni de Streamlit. `api/` et `workers/`
consomment le cœur via des **ports** (protocoles Python) ; `persistence/`
implémente ces ports pour PostgreSQL. Le frontend ne parle qu'HTTP/SSE à l'API
— aucun import du cœur métier côté Streamlit.

## 2. Composants

| Composant | Rôle | Dépend de |
|---|---|---|
| `config/` | `Settings` (env), `taxonomy` (niveaux, séries, alias) | rien |
| `domain/` | `CurriculumMetadata`, `Chunk`, `ScoredChunk` — modèles partagés | `config` |
| `ingestion/` | loaders (PDF/DOCX/TXT/MD) → normalize (pivot) → chunking structurel → annotation | `domain`, `config` |
| `vectorstore/` | embeddings (léger/BGE-M3), store (in-memory/Qdrant), indexer, retriever hybride | `domain` |
| `tools/` | calculatrice SymPy en sandbox | rien |
| `agent/` | frustration, hint_strategy, guardrails, LLM+fallback, graphe LangGraph, `TutorAgent` | `vectorstore`, `tools`, `domain` |
| `persistence/` | modèles ORM, repositories implémentant les ports de `agent/ports.py` | `agent.ports` (interfaces), SQLAlchemy async |
| `api/` | routes FastAPI, dépendances (tenant/session), streaming SSE, lifespan | `agent`, `persistence`, `vectorstore` |
| `workers/` | worker ARQ (ingestion asynchrone) | `ingestion`, `vectorstore`, `persistence` |
| `agent-tuteur-frontend/` | client Streamlit (HTTP/SSE uniquement) | — (aucun import du cœur) |

## 3. Flux

### 3.1 RAG temps réel avec streaming (`POST /api/chat`)

Le graphe LangGraph exécute 6 nœuds séquentiels :

```
a. retrieve_context    → RAG hybride Qdrant/in-memory, filtré par métadonnées
b. detect_frustration  → répétition + marqueurs (état de SESSION, éphémère)
c. diagnose_hint_level → échelle 0-4 selon la politique de transition
d. route_tool          → SymPy si un calcul est détecté
e. guardrail           → modération + assemblage du prompt final
f. compose_response    → génération LLM (streamée)
```

**Découpage préparation/génération.** `TutorAgent.prepare()` exécute a→e et
renvoie un objet `Prepared` contenant le prompt final assemblé, **sans**
appeler le LLM. `TutorAgent.stream()` prend ce `Prepared` et streame
`generate_stream()` séparément. Ce découpage permet à `api/routes/chat.py`
d'émettre l'événement SSE `{meta: {...}}` (niveau d'indice, sources, outil,
frustration) **avant** le premier token de la réponse, sans attendre la fin de
la génération pour connaître ces informations.

```
Client                API (chat.py)              TutorAgent            LLM
  │──POST /api/chat────►│                            │                  │
  │                      │──sanitize()──► 400 si injection détectée      │
  │                      │──prepare()────────────────►│                  │
  │                      │◄──Prepared (prompt, trace)─│                  │
  │◄──SSE {meta:...}─────│                            │                  │
  │                      │──stream(prepared)──────────►│──generate_stream►│
  │◄──SSE {token:...}*───│◄───────────────────────────│◄─────────────────│
  │                      │──commit_memory()───────────►│ (écrit Progress) │
  │                      │──persist conversation/messages (Postgres)      │
  │◄──SSE {done:{msg_id}}│                            │                  │
```

Persistance : la mémoire élève (`Progress`) et l'audit (`AuditLog`) sont écrits
par le nœud `guardrail`/`compose_response` via des **ports injectés par
requête** (`memory=`, `audit=` passés à `prepare()`/`respond()`), liés à la
session Postgres de la requête HTTP en cours — un seul `TutorAgent` (singleton
applicatif) sert toutes les requêtes concurrentes sans état partagé entre elles.
Les messages de conversation sont persistés **après** la fin du flux de tokens
(pas de blocage token-par-token) mais **avant** l'événement `done`, car celui-ci
transporte le `message_id` fraîchement créé.

### 3.2 Ingestion asynchrone (`POST /api/documents`)

```
Client        API (documents.py)      Postgres           Redis/ARQ        Worker
  │──upload────►│                        │                   │              │
  │              │──create_pending()─────►│ (status=pending)  │              │
  │              │──commit()──────────────►│                   │              │
  │◄─document_id─│                        │                   │              │
  │              │──enqueue_job()─────────────────────────────►│              │
  │              │  (ou BackgroundTasks si Redis indisponible) │──dequeue────►│
  │              │                        │                   │              │──process_document()
  │              │                        │                   │              │  (extract→normalize→chunk→annotate)
  │              │                        │                   │              │──embed+upsert (Indexer)
  │              │                        │◄──update_status────────────────────│  (indexed|failed)
  │──GET /status─►│──sondage 500ms───────►│                   │              │
  │◄──SSE {status}│                        │                   │              │
```

Le worker ARQ (`workers/ingestion_worker.py`) et le repli `BackgroundTasks`
(même processus que l'API, si Redis est injoignable au démarrage) exécutent
**exactement le même code** de pipeline (`ingestion.pipeline.process_document`
+ `vectorstore.indexer.Indexer`) — seul l'exécuteur change. C'est la
dégradation gracieuse : l'upload fonctionne sans Redis, avec une asynchronie
plus limitée (même processus).

**Limitation multi-processus connue.** Avec `VECTOR_BACKEND=memory` (défaut
hors-ligne), chaque processus (API, worker) a son **propre** store en mémoire.
Un document ingéré par le worker n'est donc pas visible en recherche/chat côté
API si les deux tournent en processus séparés. `VECTOR_BACKEND=qdrant` (serveur
externe partagé, configuration de `docker-compose.dev.yml`) résout ce point —
c'est la configuration recommandée dès qu'un worker séparé est utilisé.

## 4. Frontières de responsabilité

- **Cœur métier** (`agent/`, `vectorstore/`, `ingestion/`, `tools/`) : aucune
  dépendance à FastAPI, SQLAlchemy (hormis les *protocoles* de `agent/ports.py`,
  qui ne sont pas couplés à une implémentation), ou Streamlit. Testable
  entièrement hors-ligne (mock LLM, store in-memory, SQLite pour les
  repositories).
- **`agent/ports.py`** : interfaces (`StudentMemoryPort`, `AuditLogPort`) —
  le cœur en dépend, `persistence/` les implémente. Découplage classique
  d'inversion de dépendance : le cœur ne connaît pas Postgres.
- **`persistence/`** : traduit les ports en requêtes SQLAlchemy async. Ne
  contient aucune règle pédagogique (pas de calcul de niveau d'indice, pas de
  détection de frustration ici).
- **`api/`** : orchestration HTTP uniquement (validation Pydantic, dépendances,
  streaming SSE, rate limiting, CORS). Ne réimplémente aucune règle métier —
  délègue tout à `TutorAgent`/`Indexer`/les repositories.
- **`workers/`** : même remarque — le worker ne fait qu'invoquer le pipeline
  d'ingestion du cœur.
- **`agent-tuteur-frontend/`** : aucun accès direct au cœur, à la base ou au
  vectorstore. Seul `services/api_client.py` communique avec l'API (HTTP/SSE).

## 5. Mapping taxonomie curriculaire

`domain.models.CurriculumMetadata` fait foi — aucun schéma parallèle. Un chunk
porte : `niveau, classe, serie, serie_alias[], discipline, chapitre,
competence, examen_associe, type_chunk, source_document`.

- **Filtrage retriever** (`vectorstore/retriever.py::build_filters`) : traduit
  un contexte curriculaire (dict) en filtres de store sur les champs indexés
  (`niveau, classe, serie, discipline, chapitre, type_chunk`). Le champ
  `serie` est **étendu** à tous ses alias équivalents
  (`config.taxonomy.serie_aliases`) avant filtrage : une question mentionnant
  « STIDD1 » atteint des chunks annotés « T1 ».
- **Annotation ingestion** (`ingestion/annotation.py`) : fusionne frontmatter
  du document, métadonnées du formulaire d'upload, et intitulés de chunks
  (chapitre/compétence détectés par le chunking structurel) en un objet
  `CurriculumMetadata` unique par chunk.
- **Persistance** : la taxonomie ne vit **pas** en base relationnelle — elle
  n'existe que comme métadonnées de chunk dans le vectorstore. Postgres ne
  stocke que la mémoire élève, l'audit, les conversations/messages/feedback et
  les métadonnées de documents (statut d'ingestion).

## 6. Isolation multi-tenant

`tenant_id` figure sur les 6 tables Postgres (y compris `messages`/`feedback`,
dénormalisé depuis leur parent — écart volontaire par rapport à un schéma qui
ne l'aurait mis que sur les tables racines, pour simplifier le filtrage et les
policies RLS sans jointure). Défense en profondeur à deux niveaux :

1. **Applicatif** : chaque méthode de repository filtre explicitement par
   `tenant_id` (jamais de requête sans ce filtre).
2. **RLS Postgres** (migration `0002_enable_rls`) : policy `tenant_isolation`
   sur chaque table, comparée à `current_setting('app.tenant_id')`, positionné
   par `persistence.db.set_tenant_context` pour la session de la requête.
   **Condition impérative** : le rôle de connexion applicatif doit être
   **non-superuser** (`NOSUPERUSER NOBYPASSRLS`) — un superuser Postgres
   contourne toujours RLS. Voir `agent-tuteur-deploy/postgres-init/01-app-role.sh`.

Le tenant est lu depuis l'en-tête `X-Tenant-Id` (défaut `settings.default_tenant`) ;
l'authentification JWT complète est différée (cf. ADR).
