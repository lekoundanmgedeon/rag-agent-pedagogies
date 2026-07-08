# Rapport technique — Agent Tuteur Sénégal

*Document de présentation pour l'équipe technique : architecture globale,
structure du projet, et justification de chaque choix technologique et
architectural. Complète (ne remplace pas) `docs/architecture.md`, `docs/api.md`
et `docs/adr/` — ce rapport est le fil narratif qui les relie, avec les
alternatives écartées et le raisonnement derrière chaque décision.*

---

## Table des matières

1. [Contexte et vision produit](#1-contexte-et-vision-produit)
2. [Vue d'ensemble de l'architecture](#2-vue-densemble-de-larchitecture)
3. [Structure du projet](#3-structure-du-projet)
4. [Stack technique — défense de chaque outil](#4-stack-technique--défense-de-chaque-outil)
5. [Décisions d'architecture clés](#5-décisions-darchitecture-clés)
6. [Flux principaux](#6-flux-principaux)
7. [Stratégie de test](#7-stratégie-de-test)
8. [Sécurité et conformité](#8-sécurité-et-conformité)
9. [Limites connues et dette technique](#9-limites-connues-et-dette-technique)
10. [Prochaines étapes](#10-prochaines-étapes)

---

## 1. Contexte et vision produit

L'objectif est un agent tuteur pédagogique pour le programme scolaire
sénégalais (préscolaire → Baccalauréat), avec une posture **socratique** :
face à une question, l'agent ne donne pas la réponse immédiatement — il guide
par indices progressifs, sur le modèle Khanmigo. C'est le choix qui structure
tout le reste de l'architecture : ce n'est pas un chatbot RAG générique, c'est
un système avec une **politique pédagogique explicite** (l'échelle d'indice
0→4, la détection de blocage) qui doit rester auditable et modifiable
indépendamment de la génération de texte elle-même.

Quatre différenciateurs guident les choix techniques qui suivent :

- Une **échelle d'indice graduée** (pas un binaire indice/réponse) pilotée par
  une politique de seuils explicite, pas laissée à l'appréciation du LLM.
- Une **détection de blocage/frustration** qui adapte le niveau d'indice en
  cours de conversation.
- Une **traçabilité pédagogique** distincte de la mémoire élève, pour les
  enseignants/l'institution.
- Une **taxonomie curriculaire nationale** (niveaux, séries avec double
  nomenclature) comme axe de filtrage du RAG, pas une métadonnée accessoire.

---

## 2. Vue d'ensemble de l'architecture

```
┌─────────────────────┐        ┌──────────────────────────────────────┐
│  agent-tuteur-       │  HTTP  │  agent-tuteur-api                    │
│  frontend             │◄──────►│  ┌────────────────────────────────┐ │
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

Le principe qui gouverne tout : le **cœur métier** (`agent/`, `vectorstore/`,
`ingestion/`, `tools/`, `config/`, `domain/`) ne dépend jamais de FastAPI, de
SQLAlchemy côté logique, ni de Streamlit. C'est une architecture **ports &
adaptateurs** (hexagonale) : le cœur définit des interfaces (`agent/ports.py`),
`persistence/` les implémente pour Postgres, `api/` et `workers/` orchestrent
le cœur pour le web et la queue. Un test du cœur ne nécessite jamais de lancer
une base de données ; un changement de framework web n'impliquerait de
toucher qu'`api/`.

**Pourquoi c'est un choix et pas une évidence.** Il aurait été plus rapide,
pour un premier jet, d'écrire les routes FastAPI directement sur SQLAlchemy et
d'y injecter la logique d'indice/frustration inline. Le coût de la séparation
(des ports, deux graphes LangGraph, des repositories qui semblent
« bureaucratiques » pour une V1) est réel. Le bénéfice attendu : le cœur (donc
la politique pédagogique — la partie la plus susceptible d'évoluer avec les
retours enseignants) reste testable en quelques millisecondes sans
infrastructure, et n'importe quelle pièce périphérique (Qdrant → pgvector,
FastAPI → autre chose, Streamlit → React) est remplaçable sans toucher au
raisonnement pédagogique. Sur un projet destiné à itérer sur la pédagogie
plus que sur l'infrastructure, ce compromis a semblé justifié.

---

## 3. Structure du projet

```
rag-agent-pedagogie/
├── agent-tuteur-api/           Backend : cœur métier + API + worker
│   ├── src/agent_tuteur/
│   │   ├── config/             Settings (env) + taxonomie curriculaire
│   │   ├── domain/              Modèles partagés (CurriculumMetadata, Chunk, ScoredChunk)
│   │   ├── ingestion/           loaders → normalize (pivot) → chunking → annotation
│   │   ├── vectorstore/         embeddings, store (in-memory/Qdrant), indexer, retriever
│   │   ├── tools/                Calculatrice SymPy en sandbox
│   │   ├── agent/                frustration, hint_strategy, guardrails, LLM+fallback, graphe LangGraph
│   │   ├── persistence/          Modèles ORM + repositories (implémentent agent/ports.py)
│   │   ├── api/                  Routes FastAPI, dépendances, streaming SSE, lifespan
│   │   └── workers/               Worker ARQ (ingestion asynchrone)
│   ├── migrations/                Alembic (schéma + RLS)
│   ├── tests/                     Miroir de la structure src/ (unit + intégration)
│   ├── corpus/                    5 documents d'exemple (format pivot, annotés)
│   ├── scripts/demo.py            Démo 100% hors-ligne (mock + in-memory)
│   ├── Dockerfile, pyproject.toml, requirements.txt, .env.example
│
├── agent-tuteur-frontend/       Client Streamlit — AUCUN accès direct au cœur
│   ├── streamlit_app.py          Page Chat (accueil)
│   ├── pages/                    Upload, Progression
│   ├── services/api_client.py    Seul point de contact avec le backend (HTTP/SSE)
│   ├── Dockerfile, requirements.txt, .env.example
│
├── agent-tuteur-deploy/          Orchestration
│   ├── docker-compose.dev.yml    Postgres+Redis+Qdrant+api+worker+frontend
│   ├── docker-compose.prod.yml   Secrets via .env.prod, nginx en frontal
│   ├── nginx/nginx.conf           SSL, rate limiting, en-têtes SSE/WebSocket
│   ├── postgres-init/             Rôle applicatif non-superuser (condition RLS)
│   └── scripts/                   setup.sh, deploy.sh, backup.sh
│
└── docs/
    ├── architecture.md            Composants, flux, frontières, mapping taxonomie
    ├── api.md                     Chaque endpoint (requête/réponse/SSE)
    ├── adr/0001…0008               8 décisions d'architecture (format court)
    ├── migration.md                Méthode d'import de données antérieures
    └── RAPPORT_TECHNIQUE.md        Ce document
```

**Pourquoi trois sous-projets séparés (et pas un monorepo Python unique avec
un seul `pyproject.toml`).** Chacun a un cycle de déploiement et des
dépendances propres : le frontend n'a besoin ni de SQLAlchemy ni de LangGraph,
l'API n'a besoin ni de Streamlit. Séparer les `requirements.txt` et
`Dockerfile` évite qu'une image de déploiement embarque des dépendances
inutiles (poids de l'image, surface d'attaque), et permet de scaler l'API et
le frontend indépendamment (`docker compose up --scale worker=3` par exemple,
sans toucher au frontend).

---

## 4. Stack technique — défense de chaque outil

Pour chaque outil : pourquoi celui-ci, ce qui a été écarté, et le compromis
assumé.

### Python 3.11+ / async de bout en bout

Tout le cœur agent (ports, LLM, graphe LangGraph) est **async**, pas juste
l'API. Alternative écartée : garder le cœur synchrone et faire tourner les
appels bloquants dans un threadpool depuis FastAPI (`run_in_executor`). Rejeté
parce que cela aurait dupliqué la logique de découpage préparation/génération
(cf. §5) entre un chemin sync (tests/démo) et un chemin thread-wrappé (API), et
parce que le LLM et Postgres sont nativement asynchrones (`httpx.AsyncClient`,
`asyncpg`) — les threads auraient été un contournement inutile plutôt qu'une
nécessité technique.

### FastAPI

Retenu pour : support natif d'`async def`, validation Pydantic intégrée
(cohérente avec les modèles du domaine déjà en Pydantic), `StreamingResponse`
pour le SSE sans bibliothèque tierce, documentation OpenAPI générée
automatiquement (`/docs`). Alternatives écartées : **Flask** (pas async
natif, SSE plus artisanal), **Django** (poids et conventions ORM qui
entreraient en conflit avec le choix de SQLAlchemy async découplé du cœur).

### LangGraph pour l'orchestration de l'agent

Le pipeline (retrieve → frustration → hint → tool → guardrail → compose) a
des étapes séquentielles mais chacune produit un état qui alimente la
suivante, avec deux points de sortie possibles (graphe de préparation a→e vs
graphe complet a→f). Un `StateGraph` avec un état typé (`AgentState`,
`TypedDict`) rend ce flux explicite et types-checké, plutôt qu'une suite
d'appels de fonctions imbriqués où l'état circule par paramètres implicites.
Alternative écartée : une chaîne de fonctions Python simple (sans framework) —
viable pour 6 étapes fixes, mais LangGraph apporte gratuitement la
compilation en deux graphes partageant les mêmes nœuds (cf. §5, découpage
streaming) sans dupliquer le code des nœuds.

### Qdrant (+ PostgreSQL, pas `pgvector` consolidé)

Développé en détail dans [ADR 0002](adr/0002-qdrant-plus-postgres.md). En
résumé pour la réunion : Qdrant offre nativement la fusion hybride dense+sparse
(RRF) et le filtrage par payload combiné à la recherche vectorielle avec index
dédiés — `pgvector` aurait demandé de recoder cette fusion côté application.
Le compromis accepté : deux systèmes à sauvegarder/superviser au lieu d'un
seul, et — point découvert **en le testant réellement**, pas en théorie — une
limitation multi-processus quand on utilise le backend in-memory de
substitution (voir §7, l'anecdote du bug de course critique).

### PostgreSQL + SQLAlchemy async + Alembic

PostgreSQL pour tout ce qui est transactionnel et interrogeable par
agrégation (mémoire élève, audit, conversations, feedback, documents) — voir
[ADR 0001](adr/0001-postgresql-relationnel.md). SQLAlchemy 2.0 en mode async
(pas l'ORM synchrone historique) pour cohérence avec le reste de la stack
asynchrone. Alembic pour les migrations : deux migrations écrites, l'une
auto-générée (schéma), l'autre manuscrite (Row Level Security — non
auto-générable, c'est du SQL brut piloté par Alembic).

### ARQ + Redis pour l'ingestion asynchrone

Détaillé dans [ADR 0004](adr/0004-ingestion-asynchrone-arq.md). Retenu plutôt
que **Celery** parce qu'ARQ s'intègre nativement à asyncio (pas de pont
sync/async à gérer), pour un besoin de queue relativement simple (un seul type
de job : ingestion de document). Repli assumé : si Redis est injoignable au
démarrage de l'API, l'ingestion bascule automatiquement sur `BackgroundTasks`
FastAPI (même processus) — le même code de pipeline est appelé dans les deux
cas, seul l'exécuteur change. Ce n'est pas un filet de sécurité théorique : il
a été testé en coupant Redis délibérément.

### Streamlit pour le frontend

Le frontend est un **client pur** de l'API (aucun import du cœur métier). Pour
un produit dont l'essentiel de la valeur est côté agent/pédagogie, Streamlit
permet une interface fonctionnelle (chat streamé, upload, tableaux de
progression) sans investir dans une SPA React/Next.js à ce stade. Le compromis
assumé : Streamlit recharge (rerun) tout le script à chaque interaction, ce
qui impose des contournements (`st.session_state`, `st.rerun()` explicite
après le streaming) plutôt qu'un modèle de composants réactifs natif — acceptable
pour un frontend de pilotage/démonstration, à reconsidérer si l'produit vise
un usage grand public à fort trafic.

### SymPy en sandbox (pas un appel LLM pour le calcul)

Un LLM est peu fiable en arithmétique/algèbre exacte. Déléguer à SymPy garantit
un résultat correct et vérifiable, avec un sandbox (garde-fous contre
`__import__`, `eval`, tokens dangereux) plutôt qu'un `eval()` Python brut sur
l'entrée élève — point de sécurité non négociable puisque l'entrée vient
directement de l'utilisateur final.

### Mistral → Ollama → Mock (chaîne de fallback LLM)

Développé dans [ADR 0003](adr/0003-mistral-ollama-mock.md). Le point clé pour
la réunion : le mock n'est pas un artefact de développement qu'on retire en
prod — c'est un maillon de résilience assumé, qui garantit qu'aucune panne de
fournisseur externe ne bloque totalement le service (dégradation, pas panne
totale), et qui rend le projet testable/démontrable sans aucune clé API.

### Docker Compose (pas Kubernetes) pour le déploiement

Pour la taille actuelle du projet (un service API, un worker, un frontend,
trois dépendances d'infra), Kubernetes ajouterait une couche opérationnelle
(manifests, ingress controller, secrets management K8s) sans bénéfice
proportionné. `docker-compose.prod.yml` couvre déjà : `restart:
unless-stopped`, health checks, secrets via `.env.prod` non commité, nginx en
frontal avec SSL/rate limiting, scaling horizontal du worker via `--scale`. Si
le produit grandit vers plusieurs instances API/besoin d'auto-scaling, K8s
redeviendrait pertinent — prématuré aujourd'hui.

### pytest + pytest-asyncio, stratégie de test à trois niveaux

Voir §7 pour le détail et l'anecdote qui justifie cette approche.

---

## 5. Décisions d'architecture clés

Cette section reprend les ADR avec un ton plus narratif, pour anticiper les
questions typiques d'une réunion technique.

### Le découpage préparation/génération (streaming SSE)

*Question anticipée : pourquoi ne pas juste streamer tout le graphe
LangGraph ?* Parce que le client a besoin du niveau d'indice et des sources
RAG **avant** le premier token de la réponse (pour les afficher immédiatement
dans l'interface), et ces informations sont disponibles dès la fin du nœud
`guardrail` (e), bien avant que le LLM ait généré quoi que ce soit. Le graphe
est donc compilé en deux variantes (a→e et a→f) qui partagent les mêmes
fonctions de nœud — `TutorAgent.prepare()` renvoie un objet `Prepared` sans
appeler le LLM, `TutorAgent.stream()` prend ce `Prepared` et streame la
génération séparément. Conséquence pratique bien réelle : la persistance des
messages de conversation a lieu **après** la fin du flux de tokens (pas de
blocage token-par-token) mais **avant** l'événement `done` SSE, car celui-ci
transporte le `message_id` fraîchement créé — un ordre d'opérations qui
mérite d'être explicite pour quiconque retouche ce code.

### `tenant_id` dès la V1, sans authentification complète

*Question anticipée : pourquoi construire le multi-tenant si le produit n'a
qu'un seul client pour l'instant ?* Parce que le retrofit du multi-tenant sur
un schéma déjà peuplé est un projet à part entière (migration de données,
fenêtre de risque de fuite inter-tenant). Le coût de l'ajouter dès la première
migration est faible ; le coût de l'ajouter après est élevé. Ce qui n'a **pas**
été fait en contrepartie, et qu'il faut avoir en tête : l'en-tête `X-Tenant-Id`
n'est aujourd'hui pas authentifié — n'importe quel client peut prétendre
appartenir à n'importe quel tenant. Acceptable pour un pilote interne,
bloquant pour une exposition publique multi-institution sans couche JWT
devant l'API (voir §9).

### Row Level Security + rôle non-superuser

Le filtrage applicatif (chaque repository filtre explicitement par
`tenant_id`) est doublé d'une policy RLS Postgres, en défense en profondeur.
Point technique découvert en testant contre un vrai Postgres (pas en lisant la
documentation) : l'image officielle `postgres:16-alpine` crée un rôle
**superuser** par défaut, et un superuser Postgres **contourne toujours** RLS,
même avec `FORCE ROW LEVEL SECURITY`. Sans un rôle applicatif dédié
(`tuteur_app`, `NOSUPERUSER NOBYPASSRLS`, créé par
`postgres-init/01-app-role.sh`), les policies RLS écrites dans la migration
0002 seraient silencieusement inopérantes en local — un piège classique qui
aurait pu passer inaperçu sans un test d'isolation explicite (voir §7).

### Format pivot Markdown + LaTeX

Toute extraction (PDF, DOCX, TXT, MD, future sortie OCR) passe par le même
normaliseur avant chunking. Le risque sans ce choix : un PDF mal extrait
(artefacts de mise en page) et une question élève tapée en LaTeX natif
vivraient dans des espaces typographiques légèrement différents, et
l'embedding diverge silencieusement — un bug de qualité de retrieval difficile
à diagnostiquer après coup, qu'il est moins coûteux de prévenir à la source.

### Chunking structurel, jamais par taille fixe

Un chunking par taille fixe (512 tokens, chevauchement) est l'approche RAG la
plus commune — et la moins adaptée ici, parce qu'un exercice d'annale doit
remonter **entier** (énoncé + indice + solution) pour que le tuteur puisse
s'appuyer dessus de façon cohérente. Le chunking suit donc la structure
pédagogique (compétence complète / chapitre / exercice indivisible), détectée
par marqueurs (`## `, `### Exercice`) avec un repli heuristique (titres
numérotés) pour les documents sans structure Markdown explicite.

---

## 6. Flux principaux

### Chat (`POST /api/chat`)

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

### Ingestion (`POST /api/documents`)

```
Client        API (documents.py)      Postgres           Redis/ARQ        Worker
  │──upload────►│                        │                   │              │
  │              │──create_pending()─────►│ (status=pending)  │              │
  │              │──commit()──────────────►│                   │              │
  │◄─document_id─│                        │                   │              │
  │              │──enqueue_job()─────────────────────────────►│──dequeue────►│
  │              │  (ou BackgroundTasks si Redis indisponible) │              │──process_document()
  │              │                        │◄──update_status────────────────────│  (indexed|failed)
  │──GET /status─►│──sondage 500ms───────►│                   │              │
  │◄──SSE {status}│                        │                   │              │
```

Un même `TutorAgent`/graphe compilé sert **toutes les requêtes concurrentes**
sans état partagé : les ports mémoire/audit (`memory=`, `audit=`) sont
injectés **par appel** à `prepare()`/`respond()`, liés à la session Postgres
de la requête en cours — pas à la construction de l'agent. C'est ce qui permet
de ne construire l'agent qu'une seule fois au démarrage de l'API tout en
respectant l'isolation entre requêtes.

---

## 7. Stratégie de test

Trois niveaux, délibérément :

1. **Cœur métier, hors-ligne** (mock LLM, vectorstore in-memory, SQLite pour
   les repositories) — rapide (quelques secondes pour toute la suite), aucune
   infrastructure requise, tourne dans n'importe quel environnement CI basique.
2. **Intégration contre infrastructure réelle** (Postgres, Redis réels) — skip
   automatique si `TEST_DATABASE_URL`/`TEST_REDIS_URL` ne sont pas définis, pour
   ne jamais bloquer un développeur sans Docker localement, tout en couvrant
   RLS, JSONB, la vraie mécanique de queue ARQ (mode *burst*).
3. **Validation manuelle bout en bout** via `docker compose up` réel (pas
   seulement `docker compose config`) — la stack complète, tous les services,
   des vraies requêtes `curl` sur chaque endpoint.

**Pourquoi le niveau 3 n'est pas optionnel.** Un test unitaire du worker ARQ en
mode *burst* (traiter les jobs en attente puis s'arrêter) passait sans
problème. Le lancement de la stack complète avec `docker compose up` — API et
worker démarrant en parallèle — a révélé une **race condition réelle** :
les deux processus tentaient de créer la collection Qdrant simultanément au
démarrage, et le perdant de la course recevait un `409 Conflict` non géré, qui
faisait **planter le worker au démarrage**. Ce bug n'était détectable que par
un test qui démarre réellement deux processus concurrents contre un vrai
service — ni un test unitaire, ni une revue de code n'auraient nécessairement
mis le doigt dessus. Le même test complet a aussi révélé un oubli plus
prosaïque : `arq`, `redis` et `qdrant-client` étaient absents de
`requirements.txt` (installés localement pendant le développement, jamais
ajoutés au fichier versionné) — l'image Docker de l'API ne démarrait donc pas.
Les deux corrections sont dans le code livré ; l'argument pour l'équipe est
que **la revue de code et les tests unitaires ne remplacent pas un vrai
`docker compose up`** avant de considérer une fonctionnalité livrée.

---

## 8. Sécurité et conformité

- **Anti-injection de prompt** : `sanitize()` détecte les tentatives de
  détournement d'instructions et rejette en HTTP 400 **avant tout appel LLM**
  — vérifié hors du générateur SSE, car le status code ne peut plus changer
  une fois le flux entamé.
- **Modération** : contenu inapproprié pour un public mineur détecté en
  entrée, réponse déviée avec bienveillance plutôt qu'un rejet sec.
- **Sandbox de calcul** : SymPy isolé des primitives dangereuses (`eval`,
  `__import__`) — l'entrée vient directement de l'élève.
- **Isolation multi-tenant** : filtrage applicatif + RLS Postgres (voir §5),
  avec le piège du rôle superuser documenté et corrigé.
- **Rate limiting à deux niveaux** : slowapi côté application (`/api/chat`,
  `/api/upload`) et nginx en frontal en production (défense en profondeur,
  utile si l'application est contournée ou si nginx sert plusieurs backends).
- **Gap assumé** : pas de JWT/authentification utilisateur complète — le
  tenant est un en-tête non authentifié. Voir §9 et
  [ADR 0006](adr/0006-tenant-id-des-le-depart.md).

---

## 9. Limites connues et dette technique

Listées sans les minimiser — un rapport technique honnête doit les nommer :

| Limite | Impact | Contournement actuel |
|---|---|---|
| Vectorstore in-memory non partagé entre processus | Un document ingéré par le worker n'est pas visible en recherche côté API si `VECTOR_BACKEND=memory` | Utiliser `VECTOR_BACKEND=qdrant` (défaut de `docker-compose.dev.yml`) dès qu'un worker séparé tourne — validé en conditions réelles |
| Client Qdrant synchrone (`qdrant_client.QdrantClient`, pas `AsyncQdrantClient`) | Bloquerait la boucle événementielle FastAPI le temps d'un appel réseau si Qdrant est utilisé en production à fort trafic | Non corrigé — acceptable en usage pilote, à corriger avant montée en charge |
| Pas d'authentification JWT | `X-Tenant-Id` non authentifié, usurpable par tout client | Acceptable pour un déploiement pilote/interne uniquement |
| Pas de stockage d'objets (fichiers originaux) | `/reindex` exige de refournir le fichier ; pas d'archive des documents sources | Documenté dans `docs/api.md` et l'ADR correspondant |
| Rendu Streamlit non vérifié en navigateur | Le frontend a été validé par compilation/imports et par la robustesse de l'API qu'il consomme, mais pas par une capture d'écran réelle | Bibliothèques système manquantes dans l'environnement de développement (pas d'accès root) — à revalider dès qu'un environnement avec navigateur est disponible |
| Statut d'ingestion exposé par sondage (pas d'événements fins) | `/api/documents/{id}/status` sonde la base toutes les 500 ms plutôt que de relayer des événements extract/normalize/chunk/embed publiés par le worker | Contrat SSE observable stable, amélioration possible sans le casser |

---

## 10. Prochaines étapes

- **Authentification JWT** devant l'API, pour remplacer l'en-tête `X-Tenant-Id`
  non authentifié — condition avant toute exposition multi-institution réelle.
- **Client Qdrant asynchrone** (`AsyncQdrantClient`) si le trafic justifie de
  lever la limitation actuelle.
- **BGE-M3 réel** en remplacement de l'embedder léger déterministe, une fois la
  qualité de retrieval mesurée sur le corpus réel INEADE.
- **Pipeline OCR** pour les documents scannés, produisant directement le
  format pivot Markdown+LaTeX (condition posée par l'ADR 0007).
- **Événements de progression fins** côté worker (extract/normalize/chunk/
  embed) publiés via Redis pub/sub, pour enrichir `/api/documents/{id}/status`
  sans changer son contrat observable.
- **Import du corpus INEADE réel**, en suivant la méthode de
  `docs/migration.md`.
