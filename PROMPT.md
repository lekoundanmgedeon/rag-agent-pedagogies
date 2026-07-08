ARRÊT OBLIGATOIRE : réalise UNIQUEMENT les étapes 1 à 3 de l'ordre de
construction, puis ARRÊTE-TOI et attends ma validation. Ne commence PAS les
étapes 4 à 8 (Postgres, API, ARQ, frontend, deploy) dans cette session.


MISSION
Construis un NOUVEAU projet from scratch : "agent-tuteur-senegal", version mature
et production-ready d'un agent tuteur pédagogique RAG pour le programme scolaire
sénégalais. Repo vide au départ. Tu ne pars d'aucun code existant : toute la
connaissance métier nécessaire est dans ce prompt.

Tu es un ingénieur logiciel senior. Applique Clean Architecture, SOLID, DRY, KISS,
séparation stricte des responsabilités. Le cœur métier ne dépend JAMAIS d'un
framework (FastAPI/Streamlit sont aux extrémités).

═══════════════════════════════════════════════════════════════════
STACK VERROUILLÉE (ne pas substituer)
═══════════════════════════════════════════════════════════════════
- Backend : FastAPI async, port 8000
- Agent : LangGraph, Python 3.11
- Vecteurs : Qdrant (Docker, hybride dense+sparse, fusion RRF, filtrage métadonnées)
- Relationnel : PostgreSQL (SQLAlchemy async + asyncpg + Alembic)
- Queue : ARQ + Redis (ingestion asynchrone non-bloquante)
- Embeddings : BGE-M3 (dense+sparse) ; backend léger déterministe par défaut (démo hors-ligne)
- LLM : Mistral API (primaire) → Ollama local (fallback) → mock (dernier recours)
- Calcul : SymPy en sandbox
- Frontend : Streamlit, CLIENT de l'API (jamais d'accès direct au cœur)

═══════════════════════════════════════════════════════════════════
SAVOIR MÉTIER À IMPLÉMENTER (référentiel complet)
═══════════════════════════════════════════════════════════════════

# Taxonomie curriculaire
Hiérarchie niveau → classe → série(secondaire) → discipline → chapitre → compétence.
- Niveaux : préscolaire, élémentaire, moyen, secondaire, EBJA.
- Examens : CFEE, BFEM, Baccalauréat.
- Séries secondaire avec alias ancienne/nouvelle nomenclature (matcher les deux) :
  S1,S2,S3,S4,S5,F6 | L1a,L1b,L'1,L2,LA | T1↔STIDD1, T2↔STIDD2, G↔STEG.
- Métadonnées par chunk : niveau, classe, serie, serie_alias[], discipline, chapitre,
  competence, examen_associe, type_chunk, source_document.
- Champs indexés Qdrant : niveau, classe, serie, discipline, chapitre, type_chunk.
- type_chunk ∈ {competence_complete, chapitre, sous_notion, exercice}.

# Format pivot (cohérence critique)
Corpus nettoyé ET sortie OCR visent le MÊME format : Markdown + LaTeX inline
($...$, $$...$$). Toute extraction (PDF/DOCX) passe par le même normaliseur, sinon
l'espace d'embedding diverge entre contenu et questions élève.

# Chunking par structure pédagogique (jamais taille fixe)
Un chunk = une compétence complète, un chapitre, ou un exercice entier. Exercice
d'annale INDIVISIBLE (énoncé+indice+solution ensemble). Marqueurs : "## " (chapitre/
compétence), "### Exercice". PDF sans marqueurs → heuristique conservatrice de titres.

# Échelle d'indice graduée 0→4
0 reformulation | 1 rappel de notion | 2 indice ciblé | 3 solution guidée pas à pas |
4 solution directe (dernier recours).
Politique de transition (seuils) :
- Base niveau 1 ; niveau 0 si question < 4 tokens.
- +1 si répétitions ≥ 2 ; +1 si frustration ≥ 0.5 (cumulables).
- Demande explicite de correction → saut direct niveau 4. Borné [0,4].

# Détection frustration/blocage (état de SESSION, non persisté)
- Répétition : similarité question courante vs N précédentes ≥ 0.8.
- Marqueurs de ton ("je comprends pas", "donne la réponse"...).
- Score = min(1, 0.3*répétitions + 0.4*marqueurs).
- Seul le résultat notable (compétence, niveau atteint) est persisté, pas l'état.

# Garde-fous
- Modération contenu (public mineur) en entrée.
- Anti-injection de prompt : patterns détectés → HTTP 400 AVANT tout appel LLM.
- Garde-fou pédagogique : contrôle du niveau d'indice appliqué.

# Traçabilité (store DISTINCT de la mémoire élève)
Par interaction : compétence mobilisée, sources RAG + scores, niveau d'indice,
outil utilisé, frustration, timestamp, student_id, tenant_id. Pour enseignants/institution.

═══════════════════════════════════════════════════════════════════
PIPELINE AGENT (LangGraph, 6 nœuds séquentiels)
═══════════════════════════════════════════════════════════════════
a. retrieve_context  → RAG hybride Qdrant filtré par métadonnées
b. detect_frustration→ répétition + marqueurs (session éphémère)
c. diagnose_hint_level→ échelle 0-4 (politique ci-dessus)
d. route_tool        → SymPy sandbox si calcul détecté
e. guardrail         → modération + application niveau d'indice
f. compose_response  → génération LLM finale (STREAMÉE)
Chaque nœud journalise un événement d'audit ; la mémoire élève est écrite au nœud f.

DÉCOUPAGE STREAMING (impératif) : a→e sont synchrones/rapides ; seule f se streame
token par token. Expose dans le cœur une méthode qui exécute a→e et renvoie le PROMPT
FINAL ASSEMBLÉ sans lancer la génération, pour que l'API streame l'appel LLM à part.

═══════════════════════════════════════════════════════════════════
LLM : fallback + streaming
═══════════════════════════════════════════════════════════════════
- Interface BaseLLM avec generate() ET generate_stream() -> Iterator[str].
- MistralLLM : POST https://api.mistral.ai/v1/chat/completions, Bearer, modèle
  configurable (défaut mistral-small-latest), streaming SSE.
- OllamaLLM : POST {OLLAMA_BASE_URL}/api/chat (défaut http://localhost:11434),
  modèle OLLAMA_MODEL (défaut qwen3:8b), stream=true. Serveur absent → exception propre.
- MockLLM : réponse pédagogique déterministe, generate_stream yield mot par mot.
- FallbackRouter : [Mistral, Ollama, Mock] si clé Mistral ; [Ollama, Mock] si Ollama
  seul ; [Mock] sinon. Bascule silencieuse à l'erreur. Documente la logique.

═══════════════════════════════════════════════════════════════════
PIPELINE D'INGESTION (asynchrone ARQ)
═══════════════════════════════════════════════════════════════════
Upload → documents(status=pending) → job ARQ :
  extract (pypdf / python-docx / lecture directe txt,md)
  → normalize (format pivot) → chunk (structurel + heuristique PDF)
  → annotate (CurriculumMetadata) → embed (BGE-M3/léger) → upsert Qdrant
  → status=indexed|failed(error). Progression exposée en SSE.

═══════════════════════════════════════════════════════════════════
API FastAPI
═══════════════════════════════════════════════════════════════════
- POST /api/chat : exécute a→e puis STREAME la génération. Émet {meta: trace} d'abord
  (hint_level, hint_label, sources, scores, tool_used, frustration_score), puis {token}*,
  puis {done: {message_id}}. Persiste conversation/message après le stream (non-bloquant).
  sanitize anti-injection AVANT tout : rejet 400 si détecté.
- POST /api/upload (multi-fichiers PDF/DOCX/TXT/MD) → document_id immédiat, job ARQ.
- GET /api/documents ; GET /api/documents/{id} ; GET /api/documents/{id}/status (SSE) ;
  DELETE /api/documents/{id} ; POST /api/documents/{id}/reindex.
- POST /api/search : recherche hybride filtrée (chunks+scores+métadonnées).
- GET /api/progression/{student_id} : historique + difficultés récurrentes.
- POST /api/messages/{id}/feedback : ±1.
- GET /health : db, redis, qdrant, llm.
Transversal : tenant lu depuis header X-Tenant-Id (défaut "default", JWT différé) ;
rate limiting (slowapi) sur /api/chat et /api/upload ; CORS ; lifespan initialise
les pools DB/Redis/Qdrant.

═══════════════════════════════════════════════════════════════════
PERSISTANCE POSTGRESQL (Alembic ; tenant_id sur TOUTES les tables)
═══════════════════════════════════════════════════════════════════
progress(id, tenant_id, student_id, competence, hint_level, question, created_at)
audit_log(id, tenant_id, student_id, question, competence, rag_sources JSONB,
          hint_level, hint_label, frustration_score, tool_used, created_at)
conversations(id, tenant_id, student_id, created_at)
messages(id, conversation_id, role, content, trace JSONB, created_at)
feedback(id, message_id, value SMALLINT CHECK value IN (-1,1), created_at)
documents(id, tenant_id, filename, doc_type, metadata JSONB, status, error, created_at)
Repositories async ; interfaces claires (StudentMemory: record/history/
recurrent_difficulties ; AuditLog: log/read). RLS activable par tenant.

═══════════════════════════════════════════════════════════════════
DÉGRADATION GRACIEUSE (premier lancement sans infra lourde)
═══════════════════════════════════════════════════════════════════
- Embeddings : léger déterministe par défaut (dense hashing n-grammes L2-normalisé +
  sparse lexical log(1+tf)) ; BGE-M3 activable (import tardif, repli si absent).
- Vecteurs : Qdrant réel recommandé ; store in-memory (dense cosine + sparse dot + RRF)
  pour dev/tests sans serveur.
- LLM : chaîne de fallback terminée par mock → ne bloque jamais.
- L'API requiert Postgres+Redis+Qdrant actifs : documente ce prérequis clairement.

═══════════════════════════════════════════════════════════════════
STRUCTURE DU DÉPÔT (multi-service)
═══════════════════════════════════════════════════════════════════
agent-tuteur-api/       (FastAPI + cœur : config, ingestion, vectorstore, tools,
                         agent, memory, traceability, guardrails, api/, workers/ ;
                         migrations/ Alembic ; tests/ ; scripts/ ; Dockerfile ;
                         pyproject.toml ; requirements.txt ; .env.example)
agent-tuteur-frontend/  (Streamlit client : streamlit_app.py, pages/, services/
                         api_client.py ; Dockerfile ; .env.example)
agent-tuteur-deploy/    (docker-compose.dev.yml = qdrant+postgres+redis+api+worker+
                         frontend ; docker-compose.prod.yml ; nginx/ SSL+rate limit+
                         headers SSE ; scripts/ setup,deploy,backup)
docs/                   (architecture.md, api.md, migration.md, adr/)
README.md

═══════════════════════════════════════════════════════════════════
CORPUS D'EXEMPLE
═══════════════════════════════════════════════════════════════════
4-6 documents .md fictifs mais réalistes au format pivot, annotés : maths TS1
(dérivées), annale Bac S1 (exercice+corrigé), physique-chimie BFEM (forces/poids),
français TL2 (dissertation). Permet une démo end-to-end avant le corpus INEADE réel.

═══════════════════════════════════════════════════════════════════
TESTS
═══════════════════════════════════════════════════════════════════
Unitaires : chunking (exercice indivisible), retriever hybride + filtrage, SymPy
(dont calcul composite), politique d'indice (base/escalade/saut direct), sanitize
(injection→400), fallback LLM (Mistral KO → Ollama). Intégration : agent end-to-end,
routes API (TestClient), worker d'ingestion (PDF fixture → chunks → Qdrant).

═══════════════════════════════════════════════════════════════════
DOCUMENTATION (exigée, solide)
═══════════════════════════════════════════════════════════════════
- README : architecture, démarrage (Postgres/Redis/Qdrant + migrate + api + worker +
  frontend), variables d'env, formats supportés, prérequis.
- docs/architecture.md : composants, flux (ingestion asynchrone ; RAG temps réel avec
  streaming ; découpage préparation/génération), frontières de responsabilité, mapping
  taxonomie.
- docs/api.md : chaque endpoint (méthode, route, description, exemple requête/réponse,
  format des événements SSE).
- docs/adr/ : un ADR par décision — PostgreSQL relationnel ; Qdrant+Postgres ; Mistral
  primaire+Ollama fallback ; ingestion ARQ ; streaming SSE avec découpage ; tenant_id
  dès le départ ; format pivot ; chunking structurel.
- docs/migration.md : import éventuel de données antérieures (best-effort).

═══════════════════════════════════════════════════════════════════
OUTILLAGE
═══════════════════════════════════════════════════════════════════
- docker-compose.dev.yml orchestrant tout. PostgreSQL en service (commentable si
  l'utilisateur a déjà Postgres local — DATABASE_URL configurable). Qdrant et Redis inclus.
- Makefile : setup, migrate (alembic upgrade), api (uvicorn), worker (arq), run
  (streamlit vers l'API), dev (api+worker+frontend), test, seed. Chaque cible documentée.
- .env.example complet : DATABASE_URL, REDIS_URL, QDRANT_URL/API_KEY, MISTRAL_API_KEY/
  MODEL, OLLAMA_BASE_URL/MODEL, EMBEDDING_BACKEND, VECTOR_BACKEND, API_BASE_URL,
  MAX_FILE_SIZE_MB, JWT_SECRET (placeholder).

═══════════════════════════════════════════════════════════════════
ORDRE DE CONSTRUCTION (commits atomiques, tests verts à chaque étape)
═══════════════════════════════════════════════════════════════════
1. Squelette repo + config/taxonomy + corpus d'exemple + pyproject/requirements.
2. Cœur RAG : embeddings (léger+BGE-M3), store (in-memory+Qdrant), indexer, retriever
   + ingestion (loaders, normalize, chunking, annotation). Tests.
3. Agent : hint_strategy, llm (mistral/ollama/mock+fallback+stream), nodes, graph,
   guardrails, tools SymPy. Tests end-to-end en mode mock/in-memory.
4. Persistance PostgreSQL + Alembic (repositories mémoire/audit). Tests.
5. API FastAPI (routes, streaming, dépendances, sanitize, rate limit, health). Tests routes.
6. Ingestion asynchrone ARQ + Redis (worker, statut SSE). Tests worker.
7. Frontend Streamlit client (chat streaming, upload+suivi, progression, feedback).
8. Deploy (docker-compose dev/prod, nginx) + documentation complète + ADR.

CRITÈRES D'ACCEPTATION
- `make migrate && make api && make worker && make run` démarre la stack.
- Upload d'un PDF via Streamlit → suivi d'indexation temps réel → question dans le chat
  → réponse EN STREAMING avec niveau d'indice + sources RAG affichés.
- Mistral en échec → Ollama prend le relais sans intervention ; si Ollama absent → mock.
- Progression élève et audit persistés en PostgreSQL, filtrés par tenant.
- Tous les tests verts ; documentation complète et cohérente.

Explore/planifie d'abord, puis construis dans l'ordre 1→8. Ne passe pas à l'étape
suivante tant que la précédente n'est pas fonctionnelle et testée. Commits atomiques.

PÉRIMÈTRE DE CETTE SESSION : étapes 1, 2 et 3 seulement.
- Étape 1 : squelette repo + config/taxonomy + corpus d'exemple + pyproject/requirements
- Étape 2 : cœur RAG (embeddings, store, indexer, retriever, ingestion) + tests
- Étape 3 : agent (hint_strategy, llm mistral/ollama/mock+fallback+stream, nodes,
  graph, guardrails, tools SymPy) + tests end-to-end en mode mock/in-memory

Quand l'étape 3 est terminée et les tests verts, ARRÊTE-TOI. Ne crée aucun fichier
lié à Postgres, FastAPI, ARQ/Redis, Streamlit ou au déploiement. Termine par :
  1. un récapitulatif de ce qui est fait,
  2. la commande exacte pour lancer la démo end-to-end (mode mock/in-memory),
  3. la liste de ce qui reste (étapes 4→8),
et attends mon feu vert avant de continuer.