# Spécification — Agent Tuteur Sénégal v2

Document de référence pour la construction *from scratch* d'une version mature de
l'agent tuteur pédagogique. Il contient tout le savoir métier et les décisions
d'architecture nécessaires pour bâtir le projet sans dépendre d'un code antérieur.

---

## 1. Vision et périmètre

Agent tuteur pédagogique **RAG + outils** pour le programme scolaire sénégalais
(préscolaire → Baccalauréat). Posture **socratique** : l'agent guide l'élève vers
la réponse par des indices progressifs plutôt que de la donner directement
(modèle Khanmigo). Il s'appuie sur un corpus curriculaire officiel et sait
déléguer le calcul à un outil symbolique.

Différenciateurs par rapport à un assistant RAG générique :
- Échelle d'indice graduée (pas binaire indice/réponse).
- Détection de blocage/frustration et adaptation.
- Traçabilité pédagogique pour enseignants/institution.
- Taxonomie curriculaire nationale comme axe de filtrage.
- Séparation stricte contenu curriculaire / données élève / audit.

---

## 2. Stack technique verrouillée

| Couche | Choix | Justification |
|---|---|---|
| Backend API | FastAPI (async), port 8000 | Async natif, idéal SSE + I/O concurrentes |
| Orchestration agent | LangGraph (Python 3.11) | Flux multi-étapes à décision conditionnelle |
| Vecteurs | Qdrant (Docker, hybrid dense+sparse, RRF) | Filtrage métadonnées + hybride natifs |
| Relationnel | PostgreSQL (SQLAlchemy async + Alembic) | Concurrence, RLS multi-tenant, transactions |
| Queue asynchrone | ARQ + Redis | Colle à l'async FastAPI, ingestion non-bloquante |
| Embeddings | BGE-M3 (dense+sparse) ; backend léger pour démo | Multilingue + hybride en un modèle |
| LLM | Mistral API (primaire) → Ollama local (fallback) → mock | Qualité + filet souverain |
| Calcul symbolique | SymPy en sandbox | Open-source, souverain, sans API tierce |
| OCR (différé) | TrOCR + pix2tex, sortie Markdown+LaTeX | Souveraineté, cohérent format pivot |
| Frontend | Streamlit, **client de l'API** | Pas d'accès direct au métier |

**Souveraineté** : les questions d'élèves (mineurs) partent vers Mistral (API
externe) uniquement en primaire ; Ollama local garantit un repli sans dépendance
externe. Ce choix est assumé et documenté (ADR).

---

## 3. Savoir métier à implémenter (référentiel)

### 3.1 Taxonomie curriculaire

Hiérarchie : `niveau → classe → série (secondaire) → discipline → chapitre → compétence`.

- **Niveaux** : préscolaire, élémentaire, moyen, secondaire, EBJA.
- **Examens** : CFEE (élémentaire), BFEM (moyen), Baccalauréat (secondaire).
- **Séries (secondaire uniquement)** avec alias ancienne/nouvelle nomenclature
  (réforme en cours) — stocker les deux pour matcher toute requête élève :
  - Scientifiques : S1, S2, S3, S4, S5, F6
  - Littéraires : L1a, L1b, L'1, L2, LA
  - Techniques/gestion : T1↔STIDD1, T2↔STIDD2, G↔STEG
- **Schéma de métadonnées** attaché à chaque chunk :
  `niveau, classe, serie, serie_alias[], discipline, chapitre, competence,
   examen_associe, type_chunk, source_document`.
- **Champs indexés** (filtrage Qdrant) : niveau, classe, serie, discipline,
  chapitre, type_chunk.
- **type_chunk** ∈ {competence_complete, chapitre, sous_notion, exercice}.

### 3.2 Format pivot (cohérence critique)

Le corpus nettoyé **et** la sortie OCR doivent viser le **même** format :
**Markdown + LaTeX inline** (`$...$`, `$$...$$`). Sinon l'espace d'embedding
diverge entre contenu curriculaire et questions élève → dégradation silencieuse
du retrieval. Toute extraction (PDF, DOCX) passe par le même normaliseur.

### 3.3 Chunking par structure pédagogique

**Jamais** de découpage par taille fixe. Un chunk = une compétence complète, un
chapitre, ou un exercice entier. Un exercice d'annale reste **indivisible**
(énoncé + indice + solution ensemble), pour que la récupération pré-réponse
remonte le trio complet. Marqueurs de convention : `## ` (chapitre/compétence),
`### Exercice` (exercice). Pour un PDF sans marqueurs, heuristique conservatrice
de détection de titres/numérotation.

### 3.4 Échelle d'indice graduée (0 → 4)

| Niveau | Nom | Contenu |
|---|---|---|
| 0 | Reformulation | Reformule la question, aucune info nouvelle |
| 1 | Rappel de notion | Rappelle règle/théorème sans l'appliquer |
| 2 | Indice ciblé | Pointe la prochaine étape sans la faire |
| 3 | Solution guidée | Décompose pas à pas, avec validation |
| 4 | Solution directe | Dernier recours |

**Politique de transition (seuils)** :
- Point d'entrée : niveau 1 ; niveau 0 si question très courte/vague (< 4 tokens).
- Escalade +1 si répétition ≥ 2 ; +1 si frustration ≥ 0.5 (cumulables).
- Demande explicite de correction → saut direct au niveau 4.
- Niveau borné à [0, 4].

### 3.5 Détection de frustration/blocage (état de session éphémère)

- **Répétition** : similarité (Jaccard/embedding) de la question courante vs les
  N dernières ; ≥ 0.8 compte comme répétition.
- **Marqueurs de ton** : formulations type « je comprends pas », « donne la
  réponse », etc.
- **Score** : `min(1, 0.3*répétitions + 0.4*marqueurs)`.
- Cet état est **de session, non persisté** dans la mémoire élève. Seul le
  résultat notable (compétence, niveau d'indice atteint) est persisté.

### 3.6 Garde-fous

- **Modération** de contenu adaptée à un public mineur (entrée).
- **Anti-injection de prompt** : détection de patterns → rejet HTTP 400 avant
  tout appel LLM (repris de la plateforme de production Node).
- **Garde-fou pédagogique** : point de contrôle du niveau d'indice appliqué.

### 3.7 Traçabilité (audit, store distinct)

Chaque interaction produit un événement auditable : compétence mobilisée, sources
RAG + scores, niveau d'indice donné, outil utilisé, frustration détectée,
timestamp, student_id, tenant_id. Destiné aux enseignants/institution. **Store
séparé** de la mémoire élève (rétention/conformité potentiellement différentes).

---

## 4. Pipeline agent (LangGraph, 6 nœuds séquentiels)

```
a. retrieve_context    → RAG hybride Qdrant filtré par métadonnées curriculaires
b. detect_frustration  → répétition + marqueurs (état de session éphémère)
c. diagnose_hint_level → échelle 0-4 selon politique de transition
d. route_tool          → SymPy (sandbox) si calcul détecté ; OCR si image
e. guardrail           → modération + application du niveau d'indice
f. compose_response    → génération LLM finale (streamée)
```

Chaque nœud écrit un événement de traçabilité. La mémoire élève est mise à jour
au nœud f (résultat notable).

**Découpage streaming (impératif)** : les nœuds a→e sont rapides et synchrones ;
seule la génération finale (f) se streame token par token. Le cœur doit exposer
une méthode qui exécute a→e et renvoie le **prompt final assemblé** sans lancer la
génération, afin que l'API streame l'appel LLM séparément.

---

## 5. Pipeline d'ingestion (asynchrone)

```
Upload (PDF/DOCX/TXT/MD) → enregistrement documents(status=pending) → job ARQ :
  extract (pypdf / python-docx / lecture directe)
  → normalize (format pivot Markdown+LaTeX)
  → chunk (structurel ; heuristique titres pour PDF bruts)
  → annotate (métadonnées CurriculumMetadata du formulaire)
  → embed (BGE-M3 / léger)
  → upsert Qdrant
  → documents.status = indexed | failed(error)
Progression exposée en SSE.
```

---

## 6. API (FastAPI)

| Méthode | Route | Description |
|---|---|---|
| POST | /api/chat | Question → réponse **streamée SSE** ({meta}, {token}*, {done}) |
| POST | /api/upload | Upload + indexation asynchrone (renvoie document_id) |
| GET | /api/documents | Liste documents (par tenant) |
| GET | /api/documents/{id} | Détail |
| GET | /api/documents/{id}/status | Progression indexation (SSE) |
| DELETE | /api/documents/{id} | Suppression |
| POST | /api/documents/{id}/reindex | Ré-indexation |
| POST | /api/search | Recherche hybride filtrée (chunks + scores) |
| GET | /api/progression/{student_id} | Historique + difficultés récurrentes |
| POST | /api/messages/{id}/feedback | Feedback ±1 |
| GET | /health | db, redis, qdrant, llm |

Événements SSE de /api/chat : d'abord `{meta: {hint_level, hint_label, sources,
scores, tool_used, frustration_score}}`, puis une série de `{token: "..."}`, enfin
`{done: {message_id}}`.

Sécurité : sanitize anti-injection (400), rate limiting (/api/chat, /api/upload),
tenant lu depuis header `X-Tenant-Id` (défaut "default"), JWT complet différé.

---

## 7. Persistance PostgreSQL (tables, tenant_id partout)

- `progress(id, tenant_id, student_id, competence, hint_level, question, created_at)`
- `audit_log(id, tenant_id, student_id, question, competence, rag_sources JSONB,
   hint_level, hint_label, frustration_score, tool_used, created_at)`
- `conversations(id, tenant_id, student_id, created_at)`
- `messages(id, conversation_id, role, content, trace JSONB, created_at)`
- `feedback(id, message_id, value SMALLINT CHECK value IN (-1,1), created_at)`
- `documents(id, tenant_id, filename, doc_type, metadata JSONB, status, error, created_at)`

Row Level Security activable par tenant (comme la plateforme Node sur les chunks).

---

## 8. Dégradation gracieuse (exécutable dès le premier lancement)

Backends « réels » activables par configuration ; défauts légers pour démarrer
sans infra lourde :
- Vecteurs : Qdrant réel (recommandé, déjà en Docker) ; in-memory possible en dev.
- Embeddings : BGE-M3 réel ; **léger déterministe** par défaut (hors-ligne).
- LLM : Mistral si clé ; sinon Ollama si dispo ; sinon **mock** pédagogique.

L'API requiert Postgres + Redis + Qdrant actifs (documenté). Le LLM ne bloque
jamais : la chaîne de fallback se termine toujours par le mock.

---

## 9. Structure du dépôt (multi-service, inspirée d'une plateforme de prod)

```
agent-tuteur-senegal/
├── agent-tuteur-api/            # backend FastAPI + cœur métier
│   ├── src/agent_tuteur/
│   │   ├── config/              settings, taxonomy
│   │   ├── ingestion/           loaders, cleaning, chunking, annotation
│   │   ├── vectorstore/         embeddings, store (qdrant/in-memory), indexer, retriever
│   │   ├── tools/               math (sympy+sandbox), ocr (stub)
│   │   ├── agent/               graph, nodes, hint_strategy, llm (mistral/ollama/mock)
│   │   ├── memory/              repository PostgreSQL
│   │   ├── traceability/        audit PostgreSQL
│   │   ├── guardrails/          moderation, sanitize (anti-injection), pédagogique
│   │   ├── api/                 main, dependencies, streaming, routes/
│   │   └── workers/             ingestion_worker (ARQ)
│   ├── migrations/              Alembic
│   ├── tests/                   unit + integration
│   ├── scripts/                 seed, migrate, ingest
│   ├── Dockerfile, pyproject.toml, requirements.txt, .env.example
├── agent-tuteur-frontend/       # Streamlit client de l'API
│   ├── streamlit_app.py, pages/, services/api_client.py
│   ├── Dockerfile, .env.example
├── agent-tuteur-deploy/         # orchestration
│   ├── docker-compose.dev.yml   (qdrant + postgres + redis + api + worker + frontend)
│   ├── docker-compose.prod.yml
│   ├── nginx/                   SSL, rate limiting, headers SSE
│   └── scripts/                 setup, deploy, backup
├── docs/                        architecture.md, api.md, migration.md, adr/
└── README.md
```

Principe transversal : le cœur (`agent/`, `vectorstore/`, `ingestion/`, `tools/`)
ne dépend jamais de FastAPI ni de Streamlit. `api/` et le frontend sont aux
extrémités. Aucun schéma de métadonnées parallèle : `CurriculumMetadata` fait foi.

---

## 10. Corpus d'exemple (pour un premier lancement démontrable)

Fournir 4-6 documents `.md` fictifs mais réalistes, au format pivot, annotés :
maths Terminale S1 (dérivées), annale Bac S1 (exercice + corrigé), physique-chimie
BFEM (forces/poids), français Terminale L2 (dissertation). Permet la démonstration
end-to-end avant l'accès au corpus officiel INEADE.

---

## 11. Décisions à consigner en ADR

1. PostgreSQL pour le relationnel (mémoire, audit, conversations, feedback).
2. Qdrant + Postgres (plutôt que pgvector consolidé).
3. Mistral primaire + Ollama fallback + mock.
4. Ingestion asynchrone ARQ/Redis.
5. Streaming SSE avec découpage préparation/génération.
6. `tenant_id` dès la première version (multi-tenant futur sans migration lourde).
7. Format pivot Markdown+LaTeX partagé corpus/OCR.
8. Chunking structurel (jamais taille fixe).