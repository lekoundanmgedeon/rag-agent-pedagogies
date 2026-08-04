# Architecture — Agent Tuteur Sénégal

## 1. Vue d'ensemble

```
┌─────────────────────┐  HTTP  ┌──────────────────────────────────────┐
│  agent-tuteur-web    │  +JWT  │  agent-tuteur-api                    │
│  (Vue 3 SPA :        │◄──────►│  ┌────────────────────────────────┐ │
│   élève + admin)     │  SSE   │  │ api/  (FastAPI, routes, deps)  │ │
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
SQLAlchemy côté logique métier, ni du frontend. `api/` et `workers/`
consomment le cœur via des **ports** (protocoles Python) ; `persistence/`
implémente ces ports pour PostgreSQL. Le frontend (SPA Vue) ne parle qu'HTTP/SSE
à l'API, authentifié par jeton JWT — aucun import du cœur métier côté frontend.

## 2. Composants

| Composant | Rôle | Dépend de |
|---|---|---|
| `config/` | `Settings` (env), `taxonomy` (niveaux, séries, alias, nature cours/complément) | rien |
| `domain/` | `CurriculumMetadata`, `Chunk`, `ScoredChunk`, `mastery` (règles de maîtrise, calcul pur) | `config` |
| `ingestion/` | `loaders/` (PDF via PyMuPDF, nettoyage, extraction de métadonnées) → normalize (pivot) → chunking structurel → annotation | `domain`, `config` |
| `vectorstore/` | embeddings (léger/BGE-M3), store (in-memory/Qdrant), indexer, retriever hybride + re-ranker pédagogique | `domain` |
| `tools/` | calculatrice SymPy en sandbox | rien |
| `agent/` | frustration, hint_strategy, guardrails, `quiz`, `verify`, LLM+fallback (Mistral/Gemini/Ollama/mock), graphe LangGraph, `TutorAgent` | `vectorstore`, `tools`, `domain` |
| `persistence/` | modèles ORM, repositories implémentant les ports de `agent/ports.py` | `agent.ports` (interfaces), SQLAlchemy async |
| `api/` | routes FastAPI, auth JWT (`security.py`, `routes/auth.py`), dépendances (identité/tenant/session), streaming SSE, lifespan | `agent`, `persistence`, `vectorstore` |
| `workers/` | worker ARQ (ingestion asynchrone) | `ingestion`, `vectorstore`, `persistence` |
| `agent-tuteur-web/` | frontend Vue 3 (SPA élève + admin, HTTP/SSE + JWT) | — (aucun import du cœur) |

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
  qui ne sont pas couplés à une implémentation), ni au frontend. Testable
  entièrement hors-ligne (mock LLM, store in-memory, SQLite pour les
  repositories).
- **`agent/ports.py`** : interfaces (`StudentMemoryPort`, `AuditLogPort`,
  `MasteryPort`, `EvaluationPort`) — le cœur en dépend, `persistence/` les
  implémente. Découplage classique d'inversion de dépendance : le cœur ne
  connaît pas Postgres. Les adaptateurs en mémoire fournis pour les tests
  appellent **le même** module de calcul (`domain/mastery.py`) que les
  repositories PostgreSQL : un test hors-ligne mesure le vrai comportement.
- **`persistence/`** : traduit les ports en requêtes SQLAlchemy async. Ne
  contient aucune règle pédagogique (pas de calcul de niveau d'indice, pas de
  détection de frustration ici).
- **`api/`** : orchestration HTTP uniquement (validation Pydantic, dépendances,
  streaming SSE, rate limiting, CORS). Ne réimplémente aucune règle métier —
  délègue tout à `TutorAgent`/`Indexer`/les repositories.
- **`workers/`** : même remarque — le worker ne fait qu'invoquer le pipeline
  d'ingestion du cœur.
- **`agent-tuteur-web/`** : aucun accès direct au cœur, à la base ou au
  vectorstore. Seul `src/services/api.js` communique avec l'API (HTTP/SSE + JWT).

## 5. Mapping taxonomie curriculaire

`domain.models.CurriculumMetadata` fait foi — aucun schéma parallèle. Un chunk
porte : `niveau, classe, serie, serie_alias[], discipline, chapitre,
competence, examen_associe, type_chunk, type_document, source_document`.

> `type_chunk` décrit un **morceau** (chapitre, exercice, solution…) ;
> `type_document` décrit le **fichier source** dont il vient (cours, TD,
> annales). Les deux ensemble décident si un morceau relève du cours —
> `config.taxonomy.est_chunk_de_cours()`. Le second signal est indispensable :
> un TD sans titres explicites est découpé en « sous-notions » et passerait
> sinon pour du cours (mesuré : 74 % des morceaux de TD du corpus).

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

`tenant_id` figure sur les **11 tables métier** Postgres (`progress`,
`audit_log`, `conversations`, `messages`, `feedback`, `documents`, plus les
cinq tables pédagogiques du §8 — y compris `messages`/`feedback`, dénormalisé
depuis leur parent, écart volontaire pour simplifier le filtrage et les policies
RLS sans jointure). La table `users` porte aussi `tenant_id` mais reste **hors
RLS** (§7). Défense en profondeur à deux niveaux :

1. **Applicatif** : chaque méthode de repository filtre explicitement par
   `tenant_id` (jamais de requête sans ce filtre).
2. **RLS Postgres** (migration `0002_enable_rls`) : policy `tenant_isolation`
   sur chaque table, comparée à `current_setting('app.tenant_id')`, positionné
   par `persistence.db.set_tenant_context` pour la session de la requête.
   **Condition impérative** : le rôle de connexion applicatif doit être
   **non-superuser** (`NOSUPERUSER NOBYPASSRLS`) — un superuser Postgres
   contourne toujours RLS. Voir `agent-tuteur-deploy/postgres-init/01-app-role.sh`.

Le tenant n'est plus déclaratif : il est **prouvé par le jeton JWT** (§7),
`get_tenant_id` le dérive du `Principal` décodé. Il n'y a plus d'en-tête
`X-Tenant-Id`.

## 7. Authentification et rôles

L'API exige un jeton JWT `Bearer` sur toutes les routes métier (`/health` reste
public). Le flux :

- **Comptes** : table `users` (migration `0005_add_users`), **hors RLS** car le
  login recherche l'utilisateur par email *avant* de connaître le tenant. Email
  unique **global** ; rôle `admin` | `teacher` | `parent` | `student`
  (migration `0007_extend_roles`) ; `student_id` relie un compte élève à
  l'identifiant utilisé par le cœur (progression, conversations, audit).
- **`api/security.py`** : hachage bcrypt des mots de passe, signature/décodage
  JWT (HS256, `JWT_SECRET`), dataclass `Principal` (user_id, tenant_id, role,
  email, student_id).
- **`api/routes/auth.py`** : `POST /api/auth/login` (émet le jeton), `GET
  /api/auth/me` (restaure la session), `POST|GET /api/auth/users` (admin).
- **`api/dependencies.py`** : `get_current_user` (décode le `Bearer` → 401 si
  invalide), `get_tenant_id` (dérivé du jeton), `require_admin` (403 sinon),
  `get_optional_user` (pour `/health` public).
- **Autorisation** : les routes de l'espace admin (`documents`, `search`,
  `logs`) exigent `require_admin` ; `chat`/`conversations` cloisonnent chaque
  élève à sa propre identité (dérivée du jeton, jamais du corps de requête).
- **Accès aux données d'un élève** — `dependencies.ensure_can_access_student()`
  est la **seule** implémentation de cette règle, appelée par `progression`,
  `evaluation`, `mastery` et `quiz/answer` :

  | Rôle | Périmètre |
  |---|---|
  | `admin` | tous les élèves de son tenant |
  | `student` | lui-même uniquement |
  | `teacher` / `parent` | seulement les élèves liés par une ligne `student_links` |
  | *(rôle inconnu)* | aucun accès — le refus est le défaut |

  Un identifiant d'élève reçu du client n'ouvre **jamais** de droit : il est
  systématiquement confronté à cette règle. Un rôle `teacher`/`parent` ne donne
  par lui-même accès à rien tant qu'aucune liaison n'existe.
- **Quiz** : la bonne réponse ne descend pas au client. Elle voyage scellée
  dans un jeton signé (`create_quiz_token`), rouvert côté serveur à la
  correction — voir [ADR 0010](adr/0010-fusion-nuru-ats.md).
- **Amorçage** : aucun compte par défaut. Premier admin via
  `scripts/create_user.py` (ou le profil `seed` du docker-compose).

## 8. Domaine pédagogique (mastery learning)

Porté du dépôt NURU lors de la fusion — voir
[ADR 0010](adr/0010-fusion-nuru-ats.md) et
[`JOURNAL_FUSION.md`](../JOURNAL_FUSION.md) modules 3 à 5.

L'idée : suivre ce qu'un élève **maîtrise**, compétence par compétence, plutôt
que compter les exercices faits.

### 8.1 Tables (migration `0006_pedagogical_progress`, toutes sous RLS)

| Table | Contenu |
|---|---|
| `concept_mastery` | Niveau de maîtrise (0.0 → 1.0) par couple (élève, compétence) |
| `exercise_results` | Historique brut de chaque exercice ou quiz terminé |
| `badges` | Badges débloqués (unicité `tenant_id, student_id, code`) |
| `recommendations` | Révisions conseillées ; auteur enseignant **ou** nul (automatique) |
| `student_links` | Quel compte parent/enseignant peut consulter quel élève |

Trois tables de NURU ont été **écartées** comme doublons : `students`
(l'identité élève est déjà `student_id`), `interactions` (doublonne `messages`),
`teachers` (un enseignant est un `User(role='teacher')` — un seul chemin
d'authentification à sécuriser).

### 8.2 Calcul de la maîtrise (`domain/mastery.py`)

Module de **calcul pur** : ni base, ni framework, testable sans rien démarrer.

Le score suit une **moyenne mobile exponentielle** (70 % de l'acquis + 30 % du
nouveau résultat). Conséquence assumée : il dépend de l'ordre des tentatives et
n'est donc pas recalculable depuis `attempts`/`successes` — mais il reste
reconstituable en rejouant `exercise_results`. C'est la raison d'être des deux
tables.

Pourquoi pas un simple ratio : deux élèves ayant 5 échecs et 5 réussites ne sont
pas dans le même état selon qu'ils progressent ou régressent.

### 8.3 Parcours dans le graphe

`detect_intent` route désormais vers **trois** postures — le défaut reste
`exercice`, celle qui ne dévoile rien :

| Intention | Branche | Comportement |
|---|---|---|
| `exercice` (défaut) | `detect_frustration → … → guardrail` | Indices socratiques gradués |
| `cours` | `course_planner → guardrail_course` | Exposé section par section, recherche « cours d'abord » |
| `quiz` | `quiz_planner → guardrail_quiz` | Génère un QCM ou vrai/faux |

Deux nœuds terminaux clôturent le **graphe complet** (pas le streaming, qui
produit la réponse hors graphe) :

- `verify_response` — contrôles déterministes (`agent/verify.py`) : vocabulaire
  hors-programme, et présence du résultat exact quand SymPy a calculé. Plus la
  validation JSON du quiz.
- `persist_progression` — met à jour la maîtrise **seulement** si le tour porte
  un résultat corrigé (`exercise_outcome`). Poser une question ne prouve rien.
